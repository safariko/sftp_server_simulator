# edi_downloader2
Version 2 of the EDI downloader (This project supports one customer one server infrastructure)

# Please note: 
- This server already has the Supervisor installed and configured. However for the documentation purpose, I will list the steps and commands that I have used to install this Supervisor server here. The first step is to install the *supervisor* by entering the following commands:  

     **sudo apt update**  
     **sudo apt upgrade**  
     **sudo apt install supervisor**  
     
  Out of box, the Supervisor install is already useful. The only thing we want to do is to enable Supervisor's web portal by entering the following command to edit the supervisor damon configuration file:  
  
     **sudo nano /etc/supervisor/supervisord.conf**
     
  Once you are in the nano editor, enter the following contents at the end of the *supervisord.conf* file:  
    
     **[inet_http_server] &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;; inet (TCP) server disabled by default**  
     **port=0:9001 &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;; ip_address:port specifier, 0:port for all iface**  
     **username=admin &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;; default is no username (open  server)**  
     **password=715 &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;; password**  
  
  Make sure you save the file before close it. That is all I did to create this Supervisor server. After that I also created the virtualenv by using the commands listed in the "Userfull commands" section. While virtualenv is NOT related to Supervisor, it is needed for this server since we are running each job under its own virtualenv. However this server contains the virtualenv that needed for job already. You have no need to create the virtualenv anymore. 
    
  Please note that **Do NOT attempt to run any of the commands, instructions stated in above section. I have did them on this server already**.  
  
- All virtualenv are located in /home/ubuntu/VENV  

- Two virtualenv have already being created on this server. One is for *helloworld*. The other is *dummy* which is shared by all the dummy EDI download jobs.  

- "helloworld" is a reference Supervisor job that you should follow when you create the new Supervisor job  

- Userfull commands that needed for this install are:

   - To create a given virtualenv such as: *helloworld*, enter:  
      **python3 -m venv helloworld**

   - Activte the virtualenv, for example virtualenv is: *helloworld*. Enter:  
   
        **source /home/ubuntu/VENV/helloworld/bin/activate**

   - Creating the package listing using 'pip3 freeze' and use the result file to install the packages:  
         **pip3 freez > requirements.txt**  
         **pip3 install -r requirements.txt**

   - Set the system time zone to EST - This is so the message time stamp will based off EST. The default is UTC:  
      **sudo rm /etc/localtime**  
      **sudo ln -s /usr/share/zoneinfo/America/New_York /etc/localtime**

   - Show the current system time zone to confirm the change you have made:   
      **timedatectl**

   - To add a new Supervisor job by symlink into the /etc/supervisor/conf.d. Use the following command:  
   
      **sudo ln -s /home/ubuntu/helloworld/helloworld.conf /etc/supervisor/conf.d/helloworld.conf**

   - To start/stop the Supervisord damon:
      **sudo service supervisor start**  
      **sudo service supervisor stop**

   - To zero out the log file. You should use the Supervisor web portal to clear the log though.  
   
        **sudo cp /dev/null /var/log/supervisor/supervisord.log**  
        **sudo cp /dev/null /var/log/supervisor/helloworld_supervisor.out.log**  
        **sudo cp /dev/null /var/log/supervisor/helloworld_supervisor.err.log**  
     please note that there is no Web Portal support to clear the the supervisord.log  

   - Supervisor control command. Use reread/update to update/activate new job:
      **sudo supervisorctl status all**  
      **sudo supervisorctl reread**  
      **sudo supervisorctl update**  

   - Change the Bash/Python scripts to make them executable:  
      **chmod +x filename**  
      or  
      **chmod 777 filename**  
      Please note 777 means readable/writeable/executable to anyone.  
      
- The folder "dummytpserver_simulator" contains a FTP server that simulates the current dummy FTO server. The reason it exists is: dummy FTP server is NOT a standard FTP server. It deletes the file once the client has downloaded that particular file. We use this simulate the target FTP server to make sure our FTP client is working correctly since hitting the live dummy FTP server will risk the loss of the actual production file(s).  
    
    

