# Code from https://gist.github.com/slayton/3913056

#!/usr/bin/python
from subprocess import Popen, PIPE
import smtplib
from socket import gaierror
import string

# This script attepts to retrieve the IP address of a specified interface.
# If successful it then emails the retrieved IP to a specified email address

#	FILL OUT THE VALUES BETWEEN THE COMMENT BLOCKS
#######################################################################
# Specify the sender credentials and recipient email address here
SENDER = {}
SENDER['addr'] = 'goelEmbedded2022@gmail.com' 
SENDER['pass'] = 'GVYaLjPieJi.!K8'
SENDER['serv'] = 'smtp.gmail.com'
SENDER['port'] = 465  # default GMAIL SMTP port

RECEIVER = {}
RECEIVER['addr'] = [ 'zn22@ic.ac.uk' ]; 
# Note: RECEIVER['addr']  must be a list (ie don't delete the brackets)!
# This allows the specification of a list of addresses ['me@addr.com', 'you@addr.com', 'them@addr.com']

# specify the interface to query
INTERFACE = 'eth0' # default interface for a Raspberry Pi

# specify the name of the computer to display in the email
HOSTNAME = Popen(['hostname'], stdout=PIPE).communicate()[0].replace('\n', '')

#######################################################################

# Execute the call to ifconfig 
# Use AWK to remove everything but the IP Address
try:
	p1 = Popen(['ifconfig', INTERFACE], stdout=PIPE)
	p2 = Popen(['awk', "/inet/ {split ($2,A,\":\"); print A[2]}"], stdout=PIPE, stdin=p1.stdout)
	
	the_ip = p2.communicate()[0].replace('\n','');
except:
	the_ip = 'FAILED'

if the_ip =='':
	the_ip = 'no address found'

SUBJECT = "%s's IP:%s on:%s" % (HOSTNAME, the_ip, INTERFACE)

# Construct the Email
TO = RECEIVER['addr']
FROM = SENDER['addr'] 
BODY = string.join((
	'From: %s' % FROM,
	'To: %s' % TO,
	'Subject: %s' % SUBJECT,
	'',
	''
	), '\r\n')

# Try to send the email
try:
	server = smtplib.SMTP_SSL( SENDER['serv'], SENDER['port'] )     # NOTE:  This is the GMAIL SSL port.
	server.login( SENDER['addr'], SENDER['pass'] )
	server.sendmail( FROM, TO, BODY )
	server.quit()

except smtplib.SMTPAuthenticationError:
	print("Error, authentication failed! Please check your username and password.")

except gaierror:
	print("Error, cannot connect to: %s!  Please ensure it is a valid smtp server." %(SENDER['serv']))