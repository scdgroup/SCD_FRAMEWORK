import readline

def get_interfaces():
    try:
        import subprocess
        result = subprocess.run(['ip', 'link'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        interfaces = []
        for line in lines:
            if ': ' in line:
                iface = line.split(': ')[1].split(':')[0]
                interfaces.append(iface)
        return interfaces
    except:
        return ['wlan0', 'eth0', 'lo']

completions = {
    'clear': ['clear'],
    'ifconfig': ['ifconfig ', 'ifconfig -a'] + [f'ifconfig {iface}' for iface in get_interfaces()],
    'nmap': ['nmap ', 'nmap -sV', 'nmap -A', 'nmap -p 80', 'nmap -sP', 'nmap -O', 'nmap -v'],
    'ping': ['ping ', 'ping 8.8.8.8', 'ping google.com', 'ping -c 4', 'ping -t 5'],
    'help': ['help '],
    'exit': ['exit'],
    '0': ['0'],
    '1': ['1'],
    '2': ['2'],
    '3': ['3'],
    '4': ['4'],
    '5': ['5'],
}

def completer(text, state):
    if not text:
        return None
    if text in completions:
        if state < len(completions[text]):
            return completions[text][state]
    else:
        matches = [cmd for cmd in completions if cmd.startswith(text)]
        if matches:
            cmd = matches[0]
            if state < len(completions[cmd]):
                return completions[cmd][state]
    return None

def display_matches(substitution, matches, longest_match_length):
    print()
    for match in matches:
        print(match, end=' ')
    print()
    readline.redisplay()

def setup_readline():
    readline.set_completer(completer)
    readline.set_completion_display_matches_hook(display_matches)
    readline.parse_and_bind('tab: complete')