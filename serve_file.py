# Very simple web server - supports GET and POST
# So, you can get your files from the pico
# You can post (upload) your files to the pico

# Imports
import time
import network
import socket
import sys
import os
import wifi_info     # The SSID and WIFI password
    
# Replace with your own SSID and WIFI password
ssid = wifi_info.ssid
wifi_password = wifi_info.wifi_password
my_ip_addr = '192.168.0.22'

# Please see https://docs.micropython.org/en/latest/library/network.WLAN.html
# Try to connect to WIFI
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Specify the IP address
wlan.ifconfig((my_ip_addr, '255.255.255.0', '192.168.0.1', '8.8.8.8'))

# Connect
wlan.connect(ssid, wifi_password)

# Wait for connect or fail
max_wait = 10
while max_wait > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    max_wait -= 1
    print('waiting for connection...')    
    time.sleep(1)
    
# Handle connection error
if wlan.status() != 3:
    # Connection to wireless LAN failed
    print('Connection failed')    
    sys.exit()
    
else:
    print('Connected')
    status = wlan.ifconfig()
    print( 'ip = ' + status[0] )
    
# Open socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Try to bind the socket
try:
    s.bind(addr)
        
except:
    print('Bind Failed - you might need to wait a minute for things to clear up');    
    sys.exit()
    
# Listen
s.listen(4)
print('listening on', addr)

# Timeout for the socket accept, i.e., s.accept()
s.settimeout(5)

# Listen for connections, serve up web page
go_page = 1
while go_page == 1:
    
    # Handle connection error
    if wlan.status() != 3:
        # Connection to wireless LAN failed
        print('Connection failed during regular operation')
        sys.exit()
        
    # Main loop
    accept_worked = 0
    try:
        print("Run s.accept()")
        cl, addr = s.accept()
        accept_worked = 1
    except:
        print('Timeout waiting on accept - reset the pico if you want to break out of this')
        time.sleep(0.4)
        
    if accept_worked == 1:
        try:
            print('client connected from', addr)
            request = cl.recv(2048)
            print("request:")
            print(request)
            request = str(request)
            
            # Default response is error message                        
            response = """<HTML><HEAD><TITLE>Error</TITLE></HEAD><BODY>Not found...</BODY></HTML>"""
            
            # Parse the request, look for POST
            post_file = request.find('POST /')
            if post_file == 2:
                print("Found post!")
                
                # Get the content length
                content_length = request.find('Content-Length:')
                user_agent     = request.find('User-Agent')
                
                print("content_length: " + str(content_length) + ", user_agent: " + str(user_agent))
                
                if (content_length != -1) & (user_agent != -1) & ((content_length + 15) < (user_agent - 4)):
                    temp_str = request[(content_length + 15) : (user_agent - 4)]
                    print("Found in post: " + temp_str)
                    
                    # Number of bytes expected from subsequent recv commands
                    content_bytes = int(temp_str)
                    
                    # Bytes read so far
                    amount_read = 0
                                                            
                    # receive bytes from socket
                    while amount_read < content_bytes:
                        # Receive some bytes
                        temp_rx_data = cl.recv(2048)
                        
                        if amount_read == 0:
                            rx_data = temp_rx_data
                        else:
                            # Join the arrays of bytes
                            rx_data = rx_data + temp_rx_data
                                                    
                        # Add to the running sum
                        amount_read = amount_read + len(temp_rx_data)
                    
                    # If you need to debug the responses, set go_page = 0 to stop the loop, then debug with the Thonny shell
                    #go_page = 0
                    
                    # Get the webkit form boundary
                    wk_form = request.find('WebKitFormBoundary')
                    wk_form_end = request.find('\\r\\n', wk_form)
                    wk_text = request[wk_form : wk_form_end]
                    
                    # Supports drag and drop of multiple files
                    done_multiple_files = 0
                    start_index = 0
                    
                    while done_multiple_files == 0:
                        # Start of the file
                        rx_data_rnrn = rx_data.find(bytearray('\r\n\r\n', 'utf-8'), start_index)
                    
                        # Near the end of the file
                        rx_data_end = rx_data.find(bytearray(wk_text, 'utf-8'), rx_data_rnrn)
            
                        # Useful rx_data
                        rx_data_use = rx_data[(rx_data_rnrn + 4) : (rx_data_end - 8)]
                    
                        # Check
                        looks_good = rx_data[(rx_data_end - 8) : (rx_data_end - 6)] == bytearray('\r\n', 'utf-8')
                    
                        if looks_good == True:
                            print('Sliced rx_data!')
                        
                        # The filename
                        rx_data_fname_start = rx_data.find(bytearray('filename', 'utf-8'), start_index)
                        rx_data_fname_end   = rx_data.find(bytearray('\r\n', 'utf-8'), rx_data_fname_start)
                        rx_data_fname = rx_data[(rx_data_fname_start + 10) : (rx_data_fname_end - 1)].decode('utf-8')
                    
                        # Try to save the file locally to the pico
                        try:
                            fid = open(rx_data_fname, 'wb')
                            fid.write(rx_data_use)
                            fid.close()
                            print('Wrote file ' + rx_data_fname)
                        except:
                            print('Could not write file...')
                            
                        start_index = rx_data_end + 1
                        
                        if rx_data.find(bytearray('\r\n\r\n', 'utf-8'), start_index) == -1:
                            done_multiple_files = 1
                        
            
            # Look for the "GET" text
            # Parse the request for the filename - in the root directory            
            base_file = request.find('GET /')            
            if base_file == 2:
                # Look for the "HTTP" text
                end_name = request.find(' HTTP')
                
                if end_name != -1:
                    # Get the filename
                    f_name = request[7 : end_name]
                    
                    # Print the filename
                    print("filename: " + f_name)
                    
                    try:                    
                        # Get the file size, in bytes
                        temp = os.stat(f_name)
                    
                        f_size_bytes = temp[6]
                    
                        fid = open(f_name, 'rb')
                        response = fid.read()
                        print(str(len(response)) + ", " + str(f_size_bytes))
                        fid.close()
                                                                        
                    except:
                        print("Issue finding file...")
                        
                                
            cl.send('HTTP/1.0 200 OK\r\nContent-Length: ' + str(len(response)) + '\r\nConnection: Keep-Alive\r\n\r\n')
            print("Sending...")
            cl.sendall(response)
            print("---->Sent!")
                
            cl.close()
            
        except OSError as e:
            cl.close()
            print('connection closed')
            

