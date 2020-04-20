import logging
import os
import sys
import argparse

import pika
import time
import boto3
from datetime import datetime

import shutil
import pathlib
import stat
import pysftp



LOG_TIME_FORMAT = '%d/%b/%Y %H:%M:%S'

mq_connection = None

# set up logging to file
logfileName = os.path.join(os.path.dirname(__file__), os.path.basename(__file__)[:-3] + '.log')

# create module logger
top_logger_name = os.path.basename(__file__)[:-3]
logger = logging.getLogger(top_logger_name)
logger.setLevel(logging.DEBUG)

# file handler
file_handler = logging.FileHandler(logfileName, 'w')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(module)s][%(funcName)s][%(lineno)d] %(message)s',
                              LOG_TIME_FORMAT)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# define a Handler which writes INFO messages or higher to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)

# # set a format which is simpler for console use
# formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', LOG_TIME_FORMAT)

# tell the handler to use this format
console.setFormatter(formatter)

# add the handler to the root logger
# logging.getLogger('').addHandler(console)
logger.addHandler(console)


def get_log_time(level):
    # LOG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    return "[{0}][{1}] ".format(datetime.now().strftime(LOG_TIME_FORMAT), level)


def publish_error_to_rabbitmq(mq_connection, exchange, routing_key, error_message):
    result = False

    try:
        mq_channel = mq_connection.channel()

        properties = pika.BasicProperties(content_type='text/plain',
                                          delivery_mode=2)

        try:
            mq_channel.basic_publish(exchange=exchange, routing_key=routing_key,
                                     body=error_message, properties=properties)
            result = True
        except Exception as err:
            result = False
            message = "error message '" + error_message + "' failed to be published to exchange " + exchange + ". " + str(
                err)
            logger.error(message)
    except Exception as e:
        message = "RabbitMQ error before publishing the error message. " + error_message
        logger.error(message)

    return result


def get_mq_connection(feed_type, config):
    mq_connection = None

    mq = config[feed_type]['rabbitmq']
    try:
        mq_credentials = pika.PlainCredentials(mq['user_name'], mq['password'])
        mq_connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=mq['host'], port=mq['port'], virtual_host=mq['virtual_host'],
            credentials=mq_credentials))
    except Exception as e:
        message = "RabbitMQ connection creation error." + str(e)
        logger.error(message)

    return mq_connection


def get_s3_client(feed_type, config):
    try:
        s3client = boto3.client('s3',
                                aws_access_key_id=config['s3']['aws_access_key_id'],
                                aws_secret_access_key=config['s3']['aws_secret_access_key']
                                )
    except Exception as e:

        s3client = None
        message = "S3 client creation error. " + str(e)
        logger.error(message)
        mq = config[feed_type]['rabbitmq']
        publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                  get_log_time("ERROR") + message)
    return s3client


# def get_sftp_connection(feed_type, config):
#     sftp_dict = config[feed_type]['sftp_server']
#     hostname = sftp_dict['host']
#     username = sftp_dict['user_name']
#     portnumber = sftp_dict['port']
#     passwordvalue = sftp_dict['password']
#
#     cnopts = pysftp.CnOpts()
#     cnopts.hostkeys = None
#
#     try:
#     # with pysftp.Connection(host=hostname, username=username, port=portnumber, password=passwordvalue, cnopts = cnopts) as pysftp:
#     # pysftp.cd(sftp_dict['source_dir'])
#
#     except Exception as e:
#         pysftp = None
#         message = "ftp connection creation error."
#         logger.error(message)
#         mq = config[feed_type]['rabbitmq']
#         publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
#                                   get_log_time("ERROR") + message)
#     return sftp


def publish_to_rabbitmq(mq_connection, exchange, exchange_type, routing_key, source_dir, file_name, feed_type,
                        s3_bucket, date_prefix, config):
    result = False

    try:
        mq_channel = mq_connection.channel()

        local_filename = os.path.join(os.path.normpath(source_dir), file_name)

        headers = {
            "data.type": "*stream",
            # "data.source": file_name,
            "data.size": os.path.getsize(local_filename),
            "data.s3bucket": s3_bucket,
            "data.s3keyprefix": date_prefix
        }

        properties = pika.BasicProperties(content_type='text/plain',
                                          headers=headers,
                                          delivery_mode=2)

        try:
            mq_channel.exchange_declare(exchange=exchange,
                                        exchange_type=exchange_type,
                                        durable=True)

            mq_channel.basic_publish(exchange=exchange, routing_key=routing_key,
                                     # body=body, properties=properties)
                                     body=file_name, properties=properties)
            result = True
            message = "File name " + file_name + " in " + source_dir + " is pushed to exchange " + exchange + "."
            logger.info(message)
        except Exception as err:
            result = False
            message = "File name " + file_name + " in " + source_dir + " failed to be pushed to exchange " + exchange + ". " + str(
                err)
            logger.error(message)
            mq = config[feed_type]['rabbitmq']
            publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                      get_log_time("ERROR") + message)
    except Exception as e:
        message = "RabbitMQ error before publishing the file. " + str(e)
        logger.error(message)
        mq = config[feed_type]['rabbitmq']
        publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                  get_log_time("ERROR") + message)

    return result


def get_s3_date_prefix(dir, file_name):
    local_file_name = os.path.join(os.path.normpath(dir), file_name)
    file_stats = os.stat(local_file_name)
    date_prefix = time.strftime("%Y/%m/%d/", time.localtime(file_stats[stat.ST_MTIME]))

    return date_prefix


def upload_to_s3(s3client, s3_bucket, source_dir, file_name, date_prefix, feed_type, config):
    result = True

    try:
        s3client.upload_file(os.path.join(os.path.normpath(source_dir), file_name), s3_bucket, date_prefix + file_name)
        message = "File " + file_name + " in " + source_dir + " is uploaded to S3 bucket " + s3_bucket + "/" + date_prefix
        logger.info(message)
    except Exception as e:
        result = False
        message = "File " + file_name + " in " + source_dir + " failed to be uploaded to S3 bucket " + s3_bucket + ". " + str(
            e)
        logger.error(message)
        mq = config[feed_type]['rabbitmq']
        publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                  get_log_time("ERROR") + message)
    return result


def copy_file(source_dir, dest_dir, file, feed_type, config):
    result = True

    try:
        shutil.copy2(os.path.join(os.path.normpath(source_dir), file), dest_dir)

        message = "File " + file + " in " + source_dir + " is copied to " + dest_dir + ". "
        logger.info(message)
    except Exception as e:
        result = False
        message = "File " + file + " in " + source_dir + " failed to be copied to " + dest_dir + ". " + str(e)
        logger.error(message)
        mq = config[feed_type]['rabbitmq']
        publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                  get_log_time("ERROR") + message)

    return result


def delete_file(dir, file, feed_type, config):
    result = True

    try:
        os.remove(os.path.join(os.path.normpath(dir), file))

        message = "File " + file + " in " + dir + " is deleteded. "
        logger.info(message)
    except Exception as e:
        result = False
        message = "File " + file + " in " + dir + " failed to be deleted. " + str(e)
        logger.error(message)
        mq = config[feed_type]['rabbitmq']
        publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                  get_log_time("ERROR") + message)

    return result


def publish_files(mq_connection, s3client, feed_type, config):
    result = True

    # date_prefix = datetime.now().strftime("%Y/%m/%d/")

    download_dir = os.path.normpath(config[feed_type]['ftp_client']['download_dir'])
    # 2018-05-12
    # s3failed_dir = os.path.normpath(config[feed_type]['ftp_client']['s3failed_dir'])
    exchange = config[feed_type]['rabbitmq']['exchange']
    exchange_type = config[feed_type]['rabbitmq']['exchange_type']
    routing_key = config[feed_type]['rabbitmq']['routing_key']

    s3_bucket = config[feed_type]['ftp_client']['s3_bucket']

    # upload file to S3
    # file_count = len(os.listdir(download_dir))
    files = [file for file in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, file))]
    file_count = len(files)
    message = "Start to publish " + str(file_count) + " files in " + download_dir
    logger.info(message)

    for file in sorted(files):
        date_prefix = get_s3_date_prefix(download_dir, file)
        result = upload_to_s3(s3client, s3_bucket, download_dir, file, date_prefix, feed_type, config)

        if not result:
            break

        if publish_to_rabbitmq(mq_connection, exchange, exchange_type, routing_key, download_dir, file, feed_type,
                               s3_bucket, date_prefix, config):
            # delete the file after publishing successfully
            delete_result = delete_file(download_dir, file, feed_type, config)

            if not delete_result:
                # failed to delete the file in download_dir
                result = False
                message = "File " + file + " in " + download_dir + " needs to be removed manually. "
                logger.error(message)
                mq = config[feed_type]['rabbitmq']
                publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                          get_log_time("ERROR") + message)

                break
        else:
            result = False
            break

    return result


def download_and_publish(feed_type, config):
    # 2018-05-12
    result = os.EX_UNAVAILABLE
    # result = 69

    message = "Start to create directories if not existing."
    logger.info(message)

    # create directory if it is not exist...
    download_dir = os.path.join(str(pathlib.Path.home()), config[feed_type]['ftp_client']['download_dir'])
    # 2018-05-12
    # s3failed_dir = os.path.join(str(pathlib.Path.home()), config[feed_type]['ftp_client']['s3failed_dir'])
    # create directories if not existing
    pathlib.Path(download_dir).mkdir(parents=True, exist_ok=True)
    # 2018-05-12
    # pathlib.Path(s3failed_dir).mkdir(parents=True, exist_ok=True)

    # get all connections
    message = "Start to get all connections."
    logger.info(message)

    s3_client = None
    sftp = None

    global mq_connection
    mq_connection = get_mq_connection(feed_type, config)
    if mq_connection:
        s3_client = get_s3_client(feed_type, config)
        if s3_client:
            message = "Successfully connected to S3 storage."
            logger.error(message)
            result = os.EX_OK
        else:
            message = "Failed to connect to S3 storage, ftp download is not performed."
            logger.error(message)
            mq = config[feed_type]['rabbitmq']
            publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'], get_log_time("ERROR") + message)

        # All three resources have being connected. Ready to work on the actual...
        # 2018-05-12
        if result == os.EX_OK:
        #if result == 0:
            message = "Start to publish previously failed files."
            logger.info(message)

            # 2018-05-12 commented out
            # # attempt to upload files in s3failed directory
            # # the file will stay if it fails to be uploaded to S3 again
            # upload_s3failed_files(s3_client, feed_type, config)

            # attempt to publish the file that previously failed to be published to RabbitMQ
            # the previously failed stays in download directory, the process stops if it fails again

            # process the files left (if any) from previous run due to error
            result = publish_files(mq_connection, s3_client, feed_type, config)

            if result:
                # files left from previous run were published successfully,
                # download new files
                message = "Start to download new files."
                logger.info(message)

                try:
                    cnopts = pysftp.CnOpts()
                    cnopts.hostkeys = None

                    sftp_dict = config[feed_type]['sftp_server']
                    hostname = sftp_dict['host']
                    username = sftp_dict['user_name']
                    portnumber = sftp_dict['port']
                    passwordvalue = sftp_dict['password']

                    with pysftp.Connection(host=hostname, username=username, port=portnumber, password=passwordvalue, cnopts=cnopts) as sftp:
                        message = "Connection to an SFTP server established successfully."
                        logger.info(message)

                        with sftp.cd(sftp_dict['source_dir']):
                            directory_structure = sftp.listdir()
                            files = directory_structure

                            # sort the file names if requested in config file
                            # files list will be modified

                            message = str(len(files)) + " files to be downloaded."
                            logger.info(message)

                            i = 0
                            for filename in files:
                                local_filename = os.path.join(os.path.normpath(download_dir), filename)
                                sftp.get(filename, local_filename)
                                i = i + 1
                                message = str(i) + ", " + filename + " is downloaded to " + download_dir
                                logger.info(message)

                                # publish downloadwed file
                                # file_count = len(os.listdir(download_dir))
                                # message = "Start to publish " + str(file_count) + " new files."
                                # sys.stdout.write(get_log_time("INFO") + "[" + str(lineno()) + "] " + message + "\n")

                                result = publish_files(mq_connection, s3_client, feed_type, config)

                                if result:
                                    message = "Downloaded file is published successfully."
                                    logger.info(message)
                                else:
                                    message = "Error occurred when publishing downloaded file,"
                                    logger.error(message)
                                    mq = config[feed_type]['rabbitmq']
                                    publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'],
                                                              mq['exception_key'], get_log_time("ERROR") + message)

                                    break
                except Exception as e:
                    sftp = None
                    message = "ftp connection creation error."
                    logger.error(message)
                    mq = config[feed_type]['rabbitmq']
                    publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                              get_log_time("ERROR") + message)



            else:
                message = "Error occurred when publishing previously failed files, ftp download is not performed."
                logger.error(message)
                mq = config[feed_type]['rabbitmq']
                publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                          get_log_time("ERROR") + message)
        else:
            message = "Connection error, ftp download is not performed."
            logger.error(message)
            mq = config[feed_type]['rabbitmq']
            publish_error_to_rabbitmq(mq_connection, mq['exception_exchange'], mq['exception_key'],
                                  get_log_time("ERROR") + message)

    else:
        message = "Failed to connect to RabbitMQ, Critical error, no further action being performed. Program will exit after clean up!! "
        logger.error(message)
        # 2018-05-12
        result = os.EX_UNAVAILABLE
        #result = 69

    # close all
    #  connections
    if sftp:
        message = "Closing FTP connection"
        logger.info(message)

        try:
            sftp.quit()
        except:
            sftp.close()

    if mq_connection:
        message = "Closing RabbitMQ Connection."
        logger.info(message)
        mq_connection.close()

    return result


def main(argv):
    program_name = os.path.basename(argv[0])
    message = program_name + " starts."
    logger.info(message)

    parser = argparse.ArgumentParser(description="EDI File Downloader")

    parser.add_argument('-s', dest='devORproduction', required=True, action='store', choices=['dev', 'production'],
                        help='Specify which system (dev or production) to download EDI files from')
    parser.add_argument('-t', dest='ediFeedType', required=True, action='store', help='Specify which kind of EDI feed to download')

    args = parser.parse_args()
    system = args.devORproduction
    system_config = CONFIG_DATA[system]

    if args.ediFeedType in [*system_config]:
        message = "system: " + system + ", feed type: " + args.ediFeedType
        logger.info(message)

        return download_and_publish(args.ediFeedType, system_config)
    else:
        message = "'" + args.ediFeedType + "'" + " is not one of the supported EDI feed types: " + str([*system_config])
        logger.error(message)

        parser.print_help(sys.stderr)

    message = program_name + " stops."
    logger.info(message)

    # 2018-05-12
    return os.EX_OK
    #return 0

if __name__ == "__main__":

    rc = main(sys.argv)

    sys.exit(rc)
