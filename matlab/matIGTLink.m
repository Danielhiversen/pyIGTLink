% install python from 
% pip install crcmod numpy
% insert(py.sys.path,int32(0),'C:\YOUR_PATH\pyIGTLink')


P = py.sys.path;
if count(P,'C:\Users\danielho\Documents\pyIGTLink\') == 0
    insert(P,int32(0),'C:\Users\danielho\Documents\pyIGTLink\');
end

% example of using pyIGTLink from matlab
IGTLink = py.importlib.import_module('pyIGTLink'); % load the IGTLink module
% py.reload(IGTLink)
server = IGTLink.PyIGTLink(int16(18944),true); % start the server 

while true
    data = repmat(150,300,200) + randn(300,200)*90;
    data(1:4,1:5)
    
    dim = size(data);
    server.add_message_to_send_queue(IGTLink.ImageMessageMatlab(reshape(data,1,dim(1)*dim(2)),[dim(1), dim(2)])); % send image message
    pause(0.1);
end

server.close_server(); % close server
