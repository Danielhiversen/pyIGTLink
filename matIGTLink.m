% example of using pyIGTLink from matlab
IGTLink = py.importlib.import_module('pyIGTLink'); % load the IGTLink module
% py.reload(IGTLink)
server = IGTLink.PyIGTLink(int16(18944),true); % start the server 

while true
    data = normrnd(100,100,300,200);
    server.AddMessageToSendQueue(IGTLink.ImageMessageMatlab(reshape(data,1,300*200),[300,200])); % send image message
    pause(0.1);
end

server.CloseConnection(); % close server