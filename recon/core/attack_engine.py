# file core/attack_engine.py
import time
import random
import traceback
from scapy.all import IP, UDP, DNS, DNSQR, sr1, send, fragment, RandShort

class AttackEngine:
    def __init__(self, config):
        self.target_domain = config.TARGET_DOMAIN
        self.interface = config.INTERFACE
        self.dns_servers = config.DNS_SERVERS
        self.legit_domains = config.LEGITIMATE_DOMAINS
        self.common_subdomains = config.COMMON_SUBDOMAINS
        self.config = config

        # لا حاجة لاختبار إرسال الحزم الخام
        # سيتم التعامل مع الأخطاء عند التنفيذ

    def execute_attack(self, attack_type, params):
        if attack_type == "dns_recon":
            return self._dns_recon(params)
        else:
            raise ValueError(f"Unknown attack type: {attack_type}")

    def _extract_dns_info(self, reply, qname, qtype):
        """استخراج المعلومات المفيدة من رد DNS (نسخة آمنة)"""
        info = {"success": False, "answers": []}
        if reply and reply.haslayer(DNS) and reply[DNS].ancount > 0:
            info["success"] = True
            for i in range(reply[DNS].ancount):
                rr = reply[DNS].an[i]
                try:
                    if hasattr(rr, 'rrname'):
                        name = rr.rrname.decode() if isinstance(rr.rrname, bytes) else str(rr.rrname)
                    else:
                        continue
                    rtype = rr.type if hasattr(rr, 'type') else 0
                    rdata = ''
                    if hasattr(rr, 'rdata'):
                        raw = rr.rdata
                        if isinstance(raw, bytes):
                            try:
                                rdata = raw.decode()
                            except:
                                rdata = str(raw)
                        else:
                            rdata = str(raw)
                    else:
                        raw = rr.getfieldval('rdata')
                        if raw:
                            rdata = str(raw)
                        else:
                            continue
                    answer = {
                        "name": name,
                        "type": rtype,
                        "rdata": rdata
                    }
                    info["answers"].append(answer)
                except Exception:
                    continue
        return info

    def _dns_recon(self, params):
        try:
            start_time = time.time()
            if params["rotate_dns"]:
                dns_server = random.choice(self.dns_servers)
            else:
                dns_server = self.dns_servers[0]

            num_subdomains = int(params["num_subdomains"])
            selected_subdomains = random.sample(self.common_subdomains, min(num_subdomains, len(self.common_subdomains)))
            
            qtype = params["query_type"]
            successful_responses = 0
            discovered_subdomains = []
            all_answers = []

            decoy_interval = 2

            for idx, sub in enumerate(selected_subdomains):
                full_domain = f"{sub}.{self.target_domain}"
                
                if params["decoy"] and (idx % decoy_interval == 0):
                    legit_domain = random.choice(self.legit_domains)
                    self._send_dns_query(legit_domain, qtype, dns_server, params, is_decoy=True)
                    time.sleep(params["delay"] / 2)

                reply = self._send_dns_query(full_domain, qtype, dns_server, params, is_decoy=False)
                if reply:
                    info = self._extract_dns_info(reply, full_domain, qtype)
                    if info["success"]:
                        successful_responses += 1
                        discovered_subdomains.append(full_domain)
                        all_answers.extend(info["answers"])

                delay_val = params["delay"] + random.uniform(0, params["jitter"])
                time.sleep(delay_val)

                if params["rotate_dns"]:
                    dns_server = random.choice(self.dns_servers)

            duration = time.time() - start_time
            total_queries = len(selected_subdomains)
            success_rate = successful_responses / total_queries if total_queries > 0 else 0.0
            success = success_rate > 0.3

            unique_ips = set()
            unique_mx = set()
            unique_ns = set()
            cnames = []
            for ans in all_answers:
                if ans["type"] == 1:
                    unique_ips.add(ans["rdata"])
                elif ans["type"] == 15:
                    unique_mx.add(ans["rdata"])
                elif ans["type"] == 2:
                    unique_ns.add(ans["rdata"])
                elif ans["type"] == 5:
                    cnames.append(ans["rdata"])

            result = {
                "success": success,
                "duration": duration,
                "metrics": {
                    "total_queries": total_queries,
                    "successful_responses": successful_responses,
                    "success_rate": success_rate,
                    "dns_server_used": dns_server,
                    "query_type": qtype,
                    "num_subdomains": num_subdomains,
                    "discovered_count": len(discovered_subdomains)
                },
                "discovered": {
                    "subdomains": discovered_subdomains,
                    "ip_addresses": list(unique_ips),
                    "mx_servers": list(unique_mx),
                    "ns_servers": list(unique_ns),
                    "cnames": cnames,
                    "total_answers": len(all_answers),
                    "all_answers": all_answers
                }
            }
            return result
        except Exception as e:
            print(f"[!] DNS Recon exception: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e), "duration": 0.0, "discovered": {}}

    def _send_dns_query(self, domain, qtype, dns_server, params, is_decoy=False):
        try:
            dns_req = DNS(
                rd=1,
                qd=DNSQR(qname=domain, qtype=qtype)
            )
            if params["random_txn_id"]:
                dns_req.id = random.randint(0, 65535)
            else:
                dns_req.id = 12345

            ip_layer = IP(dst=dns_server, ttl=random.randint(20, 125)) # تعيين TTL عشوائي لمحاكاة حركة مرور حقيقية(20, 125)
            udp_layer = UDP(sport=self._get_src_port(params), dport=53)
            packet = ip_layer / udp_layer / dns_req

            if params["fragmentation"]:
                pkts = fragment(packet, fragsize=8)
                for frag in pkts:
                    send(frag, verbose=0, iface=self.interface)
                return None
            else:
                reply = sr1(packet, timeout=3, verbose=0, iface=self.interface)
                return reply
        except Exception as e:
            if not is_decoy:
                print(f"[!] DNS query failed for {domain}: {e}")
            return None

    def _get_src_port(self, params):
        if params["source_port_random"]:
            return random.randint(49152, 65535)
        else:
            return random.randint(1024, 49151)