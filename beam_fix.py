import queue
import socket
import struct
import threading
import time


class DummyConnection:
    """
    So basically beam stalls for a bit while waiting for a packet during sim-coupling.
    We make this a little bit faster by sending it empty data, simulating a co-sim
    """

    def __init__(self, base_port) -> None:
        self.sockets: list[socket.socket] = []
        self.out_buffers = []
        self.in_buffers = []
        self.trans_ids = []
        self.base_port = base_port
    
    def add(self):
        self.out_buffers.append(bytearray(64 * 8))
        self.in_buffers.append(bytearray(888))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('localhost', self.base_port + 2*len(self.sockets)))
        sock.recv_into(self.in_buffers[-1], 888)
        #trans_id = struct.unpack_from('d', self.in_buffers[-1], 0)[0]
        trans_id = 0
        self.trans_ids.append(trans_id)
        print(f"Added dummy socket on port {self.base_port + 2*len(self.sockets)}, trans_id={trans_id}...")

        self.sockets.append(sock)
        self.step()

    def step(self):
        for i, (sock, out_buf, in_buf, id) in enumerate(zip(self.sockets, self.out_buffers, self.in_buffers, self.trans_ids)):
            struct.pack_into('d', out_buf, 0, id)
            self.trans_ids[i] += 1
            sock.sendto(out_buf, ('localhost', self.base_port + 2*i + 1))
            sock.recv_into(in_buf, 888)

    def close(self):
        for sock in self.sockets:
            sock.close()

    def __del__(self):
        self.close()

    def __copy__(self):
        raise TypeError("DummyConnection objects are not copyable")

    def __deepcopy__(self, memo):
        raise TypeError("DummyConnection objects are not copyable")

class BeamFixThread(threading.Thread):
    def __init__(self, dummy_connection: DummyConnection):
        super().__init__()
        self.dummy_connection = dummy_connection
        self.running = True
        self.message_queue = queue.Queue()
        
    def run(self):
        # Thread loop
        while self.running:
            self.dummy_connection.step()
            time.sleep(0.005)

            try:
                self.message_queue.get(False)
                print("adding...")
                self.dummy_connection.add()
            except queue.Empty:
                pass
            
    def stop(self):
        self.running = False
