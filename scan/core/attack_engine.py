import time
import random
import socket
from scapy.all import IP, TCP, sr1, send, RandShort, fragment, sniff, ICMP

class AttackEngine:
    def __init__(self, config):
        self.target = config.TARGET_IP
        self.interface = config.INTERFACE
        self.config = config

    def execute_attack(self, attack_type, params):
        if attack_type == "stealth_syn_scan":
            return self._stealth_syn_scan(params)
        elif attack_type == "fin_scan":
            return self._fin_scan(params)
        elif attack_type == "ack_scan":
            return self._ack_scan(params)
        elif attack_type == "window_scan":
            return self._window_scan(params)
        elif attack_type == "banner_grabbing":
            return self._banner_grabbing(params)
        else:
            raise ValueError(f"Unknown attack type: {attack_type}")

    def _generate_decoys(self, count):
        decoys = []
        for _ in range(count):
            decoys.append("192.168." + str(random.randint(1, 254)) + "." + str(random.randint(1, 254)))
        return decoys

    def _sniff_for_reply(self, target_ip, src_port, dst_port, timeout=2):
        """
        Synchronous sniffing to capture replies from the target.
        Essential when using fragmentation as sr1() might miss fragmented responses.
        """
        # Filter to capture replies from target to our source port
        bpf_filter = f"host {target_ip} and (tcp src port {dst_port} and tcp dst port {src_port})"
        try:
            # Capture the first matching packet
            replies = sniff(filter=bpf_filter, timeout=timeout, count=1, iface=self.interface, store=1)
            if replies:
                return replies[0]
            return None
        except Exception as e:
            print(f"Error during sniffing: {e}")
            return None

    def _send_and_sniff(self, pkt, params, src_port, dst_port):
        """
        Sends packets (with optional decoys and fragmentation) and captures the response.
        """
        # 1. Send Decoys to distract IDS
        if params.get("decoy_count", 0) > 0:
            decoys = self._generate_decoys(params["decoy_count"])
            for decoy_ip in decoys:
                decoy_pkt = IP(src=decoy_ip, dst=self.target)/pkt.payload
                send(decoy_pkt, verbose=0, iface=self.interface)
                time.sleep(0.02)

        # 2. Send the actual packet (Fragmented or Normal)
        if params.get("fragsize", 0) > 0:
            # When fragmenting, we must use sniff() because sr1() doesn't handle fragments well
            pkts = fragment(pkt, fragsize=params["fragsize"])
            for frag in pkts:
                send(frag, verbose=0, iface=self.interface)
            # Capture reply using sniffing
            return self._sniff_for_reply(self.target, src_port, dst_port)
        else:
            # Normal send/receive
            return sr1(pkt, timeout=2, verbose=0, iface=self.interface)

    def _stealth_syn_scan(self, params):
        """
        Performs a Stealth SYN Scan (Half-open).
        Logic: SYN -> SYN/ACK (Open) | RST (Closed) | No Reply (Filtered)
        """
        try:
            start_time = time.time()
            ports = getattr(self.config, 'SCAN_PORTS', [22, 80, 443, 3306, 8080])
            port_results = []
            
            for port in ports:
                src_port = RandShort()._fix()
                
                # Distractor packet (TTL=1) to confuse IDS path tracking
                if params.get('distractor', False):
                    pkt_dist = IP(dst=self.target, ttl=1)/TCP(dport=port, flags="R", sport=src_port)
                    send(pkt_dist, verbose=0, iface=self.interface)
                
                ip = IP(dst=self.target, ttl=params.get('ttl', 64))
                tcp = TCP(dport=port, flags="S", window=params.get('window', 1024), sport=src_port)
                if params.get('random_sport', False):
                    tcp.sport = RandShort()
                pkt = ip/tcp
                
                reply = self._send_and_sniff(pkt, params, src_port, port)

                state = "unknown"
                if reply is None:
                    state = "filtered"
                elif reply.haslayer(TCP):
                    if reply[TCP].flags == 0x12:  # SYN-ACK
                        state = "open"
                        # Send RST to close the connection immediately (Stealth)
                        rst = IP(dst=self.target)/TCP(dport=port, flags="R", seq=reply[TCP].ack, ack=reply[TCP].seq + 1, sport=src_port)
                        send(rst, verbose=0, iface=self.interface)
                    elif reply[TCP].flags == 0x14:  # RST-ACK
                        state = "closed"
                elif reply.haslayer(ICMP):
                    if int(reply[ICMP].type) == 3 and int(reply[ICMP].code) in [1,2,3,9,10,13]:
                        state = "filtered"
                
                port_results.append({"port": port, "state": state})
                time.sleep(params.get('delay', 0.5))
            
            duration = time.time() - start_time
            open_ports = sum(1 for p in port_results if p["state"] == "open")
            return {
                "success": open_ports > 0,
                "duration": duration,
                "port_results": port_results,
                "metrics": {
                    "open_ports": open_ports,
                    "closed_ports": sum(1 for p in port_results if p["state"] == "closed"),
                    "filtered_ports": sum(1 for p in port_results if p["state"] == "filtered")
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "duration": 0.0}

    def _window_scan(self, params):
        """
        Performs a Window Scan.
        Logic: ACK -> RST. Check window field in RST.
        If window > 0: Open | If window == 0: Closed
        """
        try:
            start_time = time.time()
            ports = getattr(self.config, 'SCAN_PORTS', [22, 80, 443, 3306, 8080])
            port_results = []
            
            for port in ports:
                src_port = RandShort()._fix()
                ip = IP(dst=self.target, ttl=params.get('ttl', 64))
                tcp = TCP(dport=port, flags="A", sport=src_port)
                if params.get('random_sport', False):
                    tcp.sport = RandShort()
                pkt = ip/tcp
                
                reply = self._send_and_sniff(pkt, params, src_port, port)

                state = "unknown"
                if reply is None:
                    state = "filtered"
                elif reply.haslayer(TCP):
                    if reply[TCP].flags & 0x04: # RST is set
                        if reply[TCP].window > 0:
                            state = "open"
                        else:
                            state = "closed"
                elif reply.haslayer(ICMP):
                    if int(reply[ICMP].type) == 3 and int(reply[ICMP].code) in [1,2,3,9,10,13]:
                        state = "filtered"
                
                port_results.append({"port": port, "state": state})
                time.sleep(params.get('delay', 0.5))
            
            duration = time.time() - start_time
            open_ports = sum(1 for p in port_results if p["state"] == "open")
            return {
                "success": open_ports > 0,
                "duration": duration,
                "port_results": port_results,
                "metrics": {
                    "open_ports": open_ports,
                    "closed_ports": sum(1 for p in port_results if p["state"] == "closed"),
                    "filtered_ports": sum(1 for p in port_results if p["state"] == "filtered")
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "duration": 0.0}

    def _banner_grabbing(self, params):
        """
        Performs Banner Grabbing by attempting to connect and read service info.
        """
        try:
            start_time = time.time()
            ports = getattr(self.config, 'SCAN_PORTS', [22, 80, 443, 3306, 8080])
            port_results = []
            banners_found = 0
            
            for port in ports:
                banner = ""
                state = "closed"
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(params.get('timeout', 3.0))
                    result = s.connect_ex((self.target, port))
                    if result == 0:
                        state = "open"
                        # Attempt to receive banner
                        try:
                            # Some services need a trigger to send banner, but we'll try raw read first
                            banner = s.recv(1024).decode('utf-8', errors='ignore').strip()
                            if banner:
                                banners_found += 1
                        except:
                            pass
                    s.close()
                except:
                    state = "error"
                
                port_results.append({"port": port, "state": state, "banner": banner})
                time.sleep(params.get('delay', 0.5))
            
            duration = time.time() - start_time
            return {
                "success": banners_found > 0,
                "duration": duration,
                "port_results": port_results,
                "metrics": {
                    "banners_found": banners_found,
                    "open_ports": sum(1 for p in port_results if p["state"] == "open")
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "duration": 0.0}

    def _generic_scan(self, params, flags):
        """
        Generic logic for FIN and ACK scans.
        FIN: No Reply -> Open|Filtered, RST -> Closed
        ACK: RST -> Unfiltered, No Reply -> Filtered
        """
        try:
            start_time = time.time()
            ports = getattr(self.config, 'SCAN_PORTS', [22, 80, 443, 3306, 8080])
            port_results = []
            
            for port in ports:
                src_port = RandShort()._fix()
                ip = IP(dst=self.target, ttl=params.get('ttl', 64))
                tcp = TCP(dport=port, flags=flags, sport=src_port)
                if params.get('random_sport', False):
                    tcp.sport = RandShort()
                pkt = ip/tcp

                reply = self._send_and_sniff(pkt, params, src_port, port)

                state = "unknown"
                if reply is None:
                    if flags == "A": # ACK scan
                        state = "filtered"
                    else: # FIN
                        state = "open_or_filtered"
                elif reply.haslayer(TCP):
                    if reply[TCP].flags & 0x04: # RST is set
                        if flags == "A":
                            state = "unfiltered"
                        else:
                            state = "closed"
                elif reply.haslayer(ICMP):
                    if int(reply[ICMP].type) == 3 and int(reply[ICMP].code) in [1,2,3,9,10,13]:
                        state = "filtered"
                
                port_results.append({"port": port, "state": state})
                time.sleep(params.get('delay', 0.5))
            
            duration = time.time() - start_time
            
            # Success definition based on scan type
            if flags == "A":
                success = any(p["state"] == "unfiltered" for p in port_results)
            else:
                success = any(p["state"] == "open_or_filtered" for p in port_results)

            return {
                "success": success,
                "duration": duration,
                "port_results": port_results,
                "metrics": {
                    "open_or_filtered_ports": sum(1 for p in port_results if p["state"] == "open_or_filtered"),
                    "closed_ports": sum(1 for p in port_results if p["state"] == "closed"),
                    "filtered_ports": sum(1 for p in port_results if p["state"] == "filtered"),
                    "unfiltered_ports": sum(1 for p in port_results if p["state"] == "unfiltered")
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "duration": 0.0}

    def _fin_scan(self, params):
        return self._generic_scan(params, flags="F")

    def _ack_scan(self, params):
        return self._generic_scan(params, flags="A")
