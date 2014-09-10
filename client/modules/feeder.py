
import os
import subprocess
import threading
#try:
#    import threading as _threading
#except ImportError:
#    import dummy_threading as _threading



##define a class to write to a fifo 
class feeder:
    def __init__(self, fifoPath, dataLines, client):

        self.client = client

        ##start a thread to send data to a a FIFO.
        self.fT = feedThread(fifoPath, dataLines, client)
        self.fT.setDaemon(True)  ##define this thread as "background"
        self.fT.start()
    
        return

class scriptThread( threading.Thread ):

    def __init__(self, argList):
        self.argList  = argList
        threading.Thread.__init__(self)

    def run(self):
        outstatus = subprocess.call(self.argList)
        

class feedThread( threading.Thread ):
    def __init__(self, fifoPath, dataLines, client):
        threading.Thread.__init__(self)
  
        self.client = client
  
        ##Save some context.
        self.fifoPath      = fifoPath
        self.dataLines     = dataLines
        self.fifoHandle    = 0

        ##create an Event which can be watched for interrupts
        self.stop_event = threading.Event()

    def run(self):
        ##blocking write some stuff
        ##This will block if noone is reading.
        try:
            self.fifoHandle  = os.open(self.fifoPath, os.O_WRONLY) 
        except:
            exit( "Client: error opening start crds pipe for write." )


        ##main loop
        line_count = self.put_lines()

        ##cleanup
        os.close(self.fifoHandle)
        self.fifoHandle = 0



    def put_lines(self):

        line_count = 0

        if self.client.cli.nlines_in > 0:
            os.write(self.fifoHandle, str(len(self.dataLines))+"\n")##send the number of lines to expect

        for op in self.dataLines:

            L = len(op)
            if L > 0 :
                space_sepped=op[0]
                for i in range(1,len(op)):
                    space_sepped = space_sepped + " " + op[i] 
            else :
                space_sepped = ""

            try:
                os.write(self.fifoHandle, space_sepped+"\n")##send each line
            except:
                print("Client failed to write to fifo, handle:     "+str(self.fifoHandle))
                print("Client failed to write to fifo, path:       "+self.fifoPath)
                print("Client failed to write to fifo, line count: "+str(line_count))
                print("Client failed to write to fifo, line was:   "+space_sepped)
                raise
                
            line_count = line_count + 1

            
            ##catch any request to exit
            if self.stop_event.isSet():
                    print("Client fed "+str(line_count)+" lines to fifo: "+self.fifoPath);
                    print("Client quitting feed on STOP event")
                    return line_count


        print("Client fed "+str(line_count)+" lines to fifo: "+self.fifoPath);
        
        return line_count


