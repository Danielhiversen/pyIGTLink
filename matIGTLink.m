% install python from 
% pip install crcmod numpy
% insert(py.sys.path,int32(0),'C:\YOUR_PATH\pyIGTLink')

% example of using pyIGTLink from matlab
IGTLink = py.importlib.import_module('pyIGTLink'); % load the IGTLink module
% py.reload(IGTLink)
server = IGTLink.PyIGTLink(int16(18944),true); % start the server 

while true
    data = repmat(150,300,200) + randn(300,200)*90;
    data(1:4,1:5)
    
    server.add_message_to_send_queue(IGTLink.ImageMessageMatlab(reshape(data,1,300*200),[300,200])); % send image message
    pause(0.1);
end

server.close_server(); % close server
