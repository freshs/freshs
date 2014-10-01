
import os
import threading
#try:
#    import threading as _threading
#except ImportError:
#    import dummy_threading as _threading



##define a class to listen on a fifo, store the output,
##and set a flag when the fifo returns EOF.
class listener:

    def __init__(self, fifoPath, returnLines):

        self.finishedNow = threading.Event() 

        ##start a thread to read data back from a FIFO.
        self.lT = listenThread(fifoPath, returnLines, self.finishedNow)
        self.lT.setDaemon(True)  ##define this thread as "background"
        self.lT.start()
    

        return


class listenThread( threading.Thread ):

    def __init__(self, fifoPath, returnLines, finishedNow):
        threading.Thread.__init__(self)

        ##Save some context.
        self.fifoPath      = fifoPath
        self.returnLines   = returnLines
        self.save_bytes    = ''  
        self.fifoHandle    = 0
        self.finishedNow   = finishedNow

        ##create an Event which can be watched for interrupts
        self.stop_event = threading.Event()

    def run(self):

         ##blocking read the return config
         while self.fifoHandle == 0: ###BUSY WAIT - FIX THIS!
                print("Client: (re)opening listen fifo:"+self.fifoPath)
                self.fifoHandle = os.open(self.fifoPath, os.O_RDONLY )
         else:
                print("Client: listen fifo is open:"+self.fifoPath)
                
         print("Client: listener thread waiting for return data")

         line = self.get_line( self.fifoHandle )
         while line :
                self.returnLines.append([line]);
                line = self.get_line( self.fifoHandle )
                ##catch any request to exit
                if self.stop_event.isSet():
                    return 

         os.close( self.fifoHandle )

         print("Client: listener thread on "+self.fifoPath+" finished...")
         self.finishedNow.set()

    ##get a newline-terminated string from the FIFO, using
    ##only low-level I/O routines.
    def get_line(self, src):
        
        if src != 0:
            
            ##read new data if we have nothing buffered
            if len(self.save_bytes) == 0:
                in_bytes   = os.read(src, 1024)##chunksize gives a maximum amount to read in one go.
            else:
                in_bytes   = self.save_bytes
                
            while in_bytes:
                ##put the chunk up to the first newline in 'line'
                ##and save the rest back to 'in_bytes'
                [line, sep, self.save_bytes] = in_bytes.partition('\n')
                if len(sep) == 0: ##if there was no newline, then wait for more bytes
                   in_bytes   = line + os.read(src, 1024)
                else:
                   return( line )
        
        return( 0 )
              
