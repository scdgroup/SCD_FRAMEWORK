import numpy as np

class RewardEngine:
    def __init__(self):
        self.used_action_signatures = set()

    def compute(self, state, action_info):
        """
        Calculates the reward based on attack success, stealth, and efficiency.
        """
        norm_alerts = state[0]
        norm_severity = state[1]
        norm_unique_sigs = state[2]
        success = state[3] 
        norm_duration = state[4]
        fragsize_used = state[5]
        decoy_count_used = state[6]
        random_sport_used = state[7]
        scan_detect = state[8]
        recon_detect = state[9]
        entropy = state[10]
        alert_rate = state[11]
        
        attack_type = action_info.get("attack_type")
        reward = 0.0

        # 1. Base Step Penalty
        reward -= 2.0

        # 2. Success Reward Logic (Unified to encourage diversity)
        is_successful = success > 0.2
        if is_successful:
            # All successful scans get the same base reward to prevent bias
            base_success_reward = 30.0
            
            # 3. 'Silent Killer' Multiplier & Evasion Bonuses
            # Evasion bonuses (fragsize, decoys, random_sport) are ONLY awarded if the attack succeeded.
            if norm_alerts == 0:
                reward += base_success_reward * 2.0 
                # Stealth Evasion Bonus (Active only on success)
                stealth_bonus = (fragsize_used * 10.0) + (decoy_count_used * 15.0) + (random_sport_used * 5.0)
                reward += stealth_bonus
            else:
                reward += base_success_reward
                # Smaller evasion bonus if detected but still succeeded
                stealth_bonus = (fragsize_used * 2.0) + (decoy_count_used * 3.0)
                reward += stealth_bonus
        else:
            # If the attack failed, evasion techniques don't get positive rewards 
            # (they might even be penalized indirectly by time/complexity)
            pass

        # 4. Detection Penalties
        reward -= norm_alerts * 45.0
        reward -= norm_severity * 55.0
        reward -= norm_unique_sigs * 35.0
        reward -= alert_rate * 25.0
        reward -= scan_detect * 35.0
        reward -= recon_detect * 25.0

        # 5. Efficiency & Complexity
        if not is_successful:
            reward -= norm_duration * 12.0
        else:
            reward -= norm_duration * 3.0

        # 6. Repetition & Diversity Penalty
        # Signature 1: Exact Action (Attack + All Params)
        action_sig = (attack_type, tuple(sorted(action_info.get("params", {}).items())))
        
        # Signature 2: Attack Type Only (To force diversity)
        # We track the last 5 attack types to penalize spamming the same attack
        if not hasattr(self, 'recent_attacks'):
            self.recent_attacks = []
        
        if action_sig in self.used_action_signatures:
            reward -= 50.0 # Heavier penalty for exact repetition
        
        # Penalty for spamming the same attack type (e.g., Stealth SYN)
        if self.recent_attacks.count(attack_type) >= 2:
            reward -= 30.0 # Force the agent to switch attack types
            
        self.recent_attacks.append(attack_type)
        if len(self.recent_attacks) > 5:
            self.recent_attacks.pop(0)

        self.used_action_signatures.add(action_sig)
        if len(self.used_action_signatures) > 1000:
            self.used_action_signatures.clear()

        return np.clip(reward / 100.0, -1.0, 1.0)

    def reset(self):
        self.used_action_signatures.clear()
        if hasattr(self, 'recent_attacks'):
            self.recent_attacks = []
