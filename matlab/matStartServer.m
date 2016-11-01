% example of using pyIGTLink from matlab
IGTLink = py.importlib.import_module('pyIGTLink'); % load the IGTLink module
% py.reload(IGTLink)
server = IGTLink.PyIGTLink(int16(18944),true); % start the server 

%server.add_message_to_send_queue(IGTLink.ImageMessageMatlab(reshape(data,1,300*200),[300,200])); % send image message

%server.close_server(); % close server
