function sendToCX(input_data) 
    igtlink_path = 'C:\Users\danielho\Documents\pyIGTLink\';
    global server;
    global IGTLink;
    persistent ctr;
   
     if isempty(ctr),
         ctr = 1;
     else
         ctr = mod(ctr, size(input_data, 4) ) + 1;
     end
     
     if isempty(IGTLink)
        'Start server'
        if count(py.sys.path, igtlink_path) == 0
            insert(py.sys.path,int32(0), igtlink_path);
        end
        IGTLink = py.importlib.import_module('pyIGTLink'); % load the IGTLink module
        server = IGTLink.PyIGTLink(int16(18944),true); % start the server 
    end

    imdata = input_data(:, :, 1, ctr);
    dim = size(imdata);
    imdata = imdata/max(imdata(:))*255;
    PData = evalin('base','PData');
    spacing = [PData.PDelta(1), PData.PDelta(3), PData.PDelta(2)];
    packet = IGTLink.ImageMessageMatlab(reshape(imdata', 1, dim(1)*dim(2)), [dim(1), dim(2)], spacing);
    %send image message
    server.add_message_to_send_queue(packet);

return
