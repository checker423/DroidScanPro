# flake8: noqa
class ScanEngine:
    def __init__(self):
        # ------------------------------------------------------------------ #
        #  Known-malicious package signatures
        #  Each entry: {"description", "category", "solution", "fix_action"}
        # ------------------------------------------------------------------ #
        self.signature_blacklist = {
            # --- Trojans ---
            "com.example.malware": {
                "description": "Known Trojan-SMS variant sending premium messages without consent.",
                "category": "Trojan",
                "solution": "Uninstall immediately. Check your carrier bill for unauthorized charges. Run a factory reset if charges appeared.",
                "fix_action": "uninstall",
            },
            "com.android.security.update": {
                "description": "Phishing app disguised as a system update, collects credentials.",
                "category": "Spyware",
                "solution": "Remove immediately and change all account passwords. Your credentials may have been stolen.",
                "fix_action": "uninstall",
            },
            "com.trojan.sms": {
                "description": "SMS Trojan sending premium-rate messages silently.",
                "category": "Trojan",
                "solution": "Uninstall and contact your carrier to block premium-rate SMS.",
                "fix_action": "uninstall",
            },
            "com.android.protect": {
                "description": "Fake antivirus app that downloads additional malware.",
                "category": "Trojan-Dropper",
                "solution": "Remove this fake AV. Scan with a legitimate security solution after removal.",
                "fix_action": "uninstall",
            },
            "com.fakeapp.whatsapp": {"category": "Fake App", "description": "Fake version of WhatsApp designed to steal contacts and messages.", "solution": "Uninstall and download official app from Play Store.", "fix_action": "uninstall"},
            "com.vanced.mod.youtube": {"category": "Modded APK", "description": "Unofficial YouTube Premium mod containing background adware.", "solution": "Uninstall to prevent data theft and battery drain.", "fix_action": "uninstall"},
            "com.loapi.miner": {"category": "Crypto Miner", "description": "Mines Monero in background, can cause battery swelling/explosion.", "solution": "Uninstall immediately to prevent hardware damage.", "fix_action": "uninstall"},
            "com.spy.app": {
                "description": "Commercial spyware silently tracking location, calls, and messages.",
                "category": "Spyware",
                "solution": "Uninstall immediately. Factory reset is strongly recommended if you believe someone installed it without your consent.",
                "fix_action": "uninstall",
            },
            # --- Adware ---
            "com.flash.light.pro": {
                "description": "Flashlight adware silently exfiltrating device data and serving intrusive ads.",
                "category": "Adware",
                "solution": "Uninstall this app. Use the built-in flashlight in your quick settings instead.",
                "fix_action": "uninstall",
            },
            "com.boost.cleaner": {
                "description": "Fake cleaner app aggressively harvesting data and displaying full-screen ads.",
                "category": "Adware",
                "solution": "Remove this app. Android manages memory automatically — no cleaner is needed.",
                "fix_action": "uninstall",
            },
            "com.security.scan.free": {
                "description": "Fake scanner distributing adware payloads in the background.",
                "category": "Adware",
                "solution": "Uninstall. Use Google Play Protect as your primary scanner.",
                "fix_action": "uninstall",
            },
            "com.phone.booster.pro": {
                "description": "Battery/speed optimizer scam harvesting contacts, location, and call logs.",
                "category": "Adware",
                "solution": "Uninstall. Go to Settings > Apps and revoke all permissions before removal.",
                "fix_action": "uninstall",
            },
            # --- Ransomware ---
            "com.super.cleaner.junk": {
                "description": "Fake utility app capable of locking files for ransom.",
                "category": "Ransomware",
                "solution": "Uninstall immediately. If files are locked, do NOT pay. Boot into safe mode to remove app, then restore from backup.",
                "fix_action": "uninstall",
            },
            "com.locker.screen": {
                "description": "Screen-locker ransomware that demands payment to unlock device.",
                "category": "Ransomware",
                "solution": "Boot into safe mode (hold Power > long-press Power Off > Safe Mode), then uninstall from Settings > Apps.",
                "fix_action": "uninstall",
            },
            # --- Stalkerware / RAT ---
            "com.remote.admin.tool": {
                "description": "Remote Administration Tool giving attacker full device control.",
                "category": "RAT",
                "solution": "Immediately uninstall and perform a factory reset. Change all passwords from a different device.",
                "fix_action": "uninstall",
            },
            "com.keylogger.stealth": {
                "description": "Keylogger recording every keystroke including passwords and banking PINs.",
                "category": "Keylogger",
                "solution": "Uninstall and factory reset. Change all passwords from a trusted device.",
                "fix_action": "uninstall",
            },

            # --- Real-world Malware Families ---
            "com.cerberus.banking": {
                "description": "Cerberus Banking Trojan — steals 2FA codes, credit card details, banking credentials via overlay attacks.",
                "category": "Banking Trojan",
                "solution": "Factory reset immediately. Contact your bank and freeze all cards. Change passwords from a safe device.",
                "fix_action": "uninstall",
            },
            "com.flubot.delivery": {
                "description": "FluBot spyware disguised as a package delivery tracking app. Spreads itself by spamming SMS to contacts.",
                "category": "Spyware/Worm",
                "solution": "Uninstall and factory reset. Warn your contacts not to click any links recently sent from your number.",
                "fix_action": "uninstall",
            },
            "com.joker.subscription": {
                "description": "Joker malware — silently subscribes you to premium WAP services by intercepting OTP codes.",
                "category": "Subscription Fraud",
                "solution": "Uninstall. Contact your carrier to cancel any unauthorized subscriptions and request a refund.",
                "fix_action": "uninstall",
            },
            "com.hummer.root": {
                "description": "Hummer Trojan — one of the most widespread Android rootkits. Gains root access and installs unwanted apps.",
                "category": "Rootkit",
                "solution": "Factory reset required. This malware survives normal uninstall. Flash stock firmware if possible.",
                "fix_action": "uninstall",
            },
            "com.agent.smith.payload": {
                "description": "Agent Smith malware — replaces legitimate apps with malicious clones, injects adware payloads silently.",
                "category": "Trojan",
                "solution": "Uninstall all unknown/duplicate apps. Reinstall legitimate apps from Play Store only.",
                "fix_action": "uninstall",
            },
            "com.spynote.rat": {
                "description": "SpyNote RAT — full remote access: screen capture, microphone, camera, files, and GPS in real time.",
                "category": "RAT",
                "solution": "Immediate factory reset. Change ALL passwords. Assume all data (photos, messages, passwords) is compromised.",
                "fix_action": "uninstall",
            },
            "com.alien.banking.stealer": {
                "description": "Alien Banking Trojan — targets 226 apps, steals credentials via overlays and 2FA interception.",
                "category": "Banking Trojan",
                "solution": "Factory reset. Contact all financial institutions. Monitor accounts for unauthorized activity.",
                "fix_action": "uninstall",
            },
            "com.ginp.banking": {
                "description": "Ginp Banking Trojan — inserts fake SMS into inbox to trick victims; steals card data via overlays.",
                "category": "Banking Trojan",
                "solution": "Factory reset and notify your bank. Block and replace all payment cards.",
                "fix_action": "uninstall",
            },
            "com.anubis.stealer": {
                "description": "Anubis Banking Malware — motion-sensor evasion, screen recording, and credential theft from 400+ apps.",
                "category": "Banking Trojan",
                "solution": "Factory reset required. Change every password and enable 2FA on all accounts.",
                "fix_action": "uninstall",
            },
            "com.hookbot.injectapp": {
                "description": "Hook malware — files exfiltration, overlay attacks, real-time screen streaming to attacker.",
                "category": "RAT/Spyware",
                "solution": "Factory reset immediately. Revoke all app permissions via Settings > Apps before removal if possible.",
                "fix_action": "uninstall",
            },
            "com.smsstealer.silent": {
                "description": "Silent SMS stealer — forwards all incoming messages (including OTPs and bank alerts) to attacker server.",
                "category": "Spyware",
                "solution": "Uninstall and factory reset. Contact your bank to disable SMS-based 2FA temporarily.",
                "fix_action": "uninstall",
            },
            "com.fake.google.play": {
                "description": "Fake Google Play Store — harvests login credentials when user 'updates' their Play account.",
                "category": "Phishing",
                "solution": "Uninstall. Only install apps from the official Google Play Store (play.google.com).",
                "fix_action": "uninstall",
            },
            "com.android.market.update": {
                "description": "Fake Android Market updater — downloads and silently installs additional malware payloads.",
                "category": "Trojan-Dropper",
                "solution": "Uninstall and scan all recently installed apps. Factory reset if device behavior is abnormal.",
                "fix_action": "uninstall",
            },
            "com.whatsapp.fake.update": {
                "description": "Fake WhatsApp update — phishing app that steals WhatsApp credentials and contact list.",
                "category": "Phishing",
                "solution": "Uninstall. Update WhatsApp only through official app store. Re-verify your WhatsApp account.",
                "fix_action": "uninstall",
            },
            "com.adspy.tracker": {
                "description": "Adspy tracker SDK — harvests device ID, IMEI, location, browsing history, and sells it to advertisers.",
                "category": "Adware/Spyware",
                "solution": "Uninstall. Revoke Location and Storage permissions from all suspicious apps in Settings.",
                "fix_action": "uninstall",
            },
            "com.photo.locker.ransom": {
                "description": "Photo Vault ransomware — encrypts personal photos and demands payment for decryption key.",
                "category": "Ransomware",
                "solution": "Do NOT pay. Boot into safe mode to remove. Restore photos from Google Photos or backup.",
                "fix_action": "uninstall",
            },
            "com.vpn.spy.logger": {
                "description": "Malicious VPN app logging all network traffic and sending it to third-party servers.",
                "category": "Spyware",
                "solution": "Uninstall and clear browser data. Use only reputable VPN providers (ProtonVPN, Mullvad).",
                "fix_action": "uninstall",
            },
            "com.toast.spyware": {
                "description": "Toast overlay spyware — silently grants itself Device Admin and accessibility permissions.",
                "category": "Spyware",
                "solution": "Go to Settings > Accessibility and revoke permissions, then uninstall. Factory reset recommended.",
                "fix_action": "uninstall",
            },
            "com.fake.battery.saver": {
                "description": "Fake battery optimizer — mines cryptocurrency using device CPU in the background.",
                "category": "Crypto-Miner",
                "solution": "Uninstall immediately. Check Settings > Battery for abnormal consumption. A reset may be needed.",
                "fix_action": "uninstall",
            },
            "com.dropper.stage2": {
                "description": "Stage-2 dropper — downloads and installs secondary payload after initial installation.",
                "category": "Trojan-Dropper",
                "solution": "Uninstall all recently-sideloaded APKs. Factory reset and only install apps from trusted sources.",
                "fix_action": "uninstall",
            },
            "com.screen.capture.stealth": {
                "description": "Stealth screen capture app — silently screenshots your screen every few minutes.",
                "category": "Stalkerware",
                "solution": "Factory reset. Assume all screen content (passwords, messages, banking apps) has been captured.",
                "fix_action": "uninstall",
            },
            "com.gps.tracker.hidden": {
                "description": "Hidden GPS tracker — continuously uploads real-time location without user knowledge.",
                "category": "Stalkerware",
                "solution": "Uninstall. Go to Settings > Location > App Permissions and audit all apps with location access.",
                "fix_action": "uninstall",
            },
            "com.coin.miner.bg": {
                "description": "Background Monero crypto-miner — drains battery, overheats device, shortens hardware lifespan.",
                "category": "Crypto-Miner",
                "solution": "Uninstall. Check Device Care for excessive CPU usage. Factory reset if overheating persists.",
                "fix_action": "uninstall",
            },
            "com.android.defaultapp.spy": {
                "description": "Disguised as a system default app — intercepts all notifications including OTPs and private messages.",
                "category": "Spyware",
                "solution": "Uninstall. Disable Notification Access for all unknown apps in Settings > Notifications.",
                "fix_action": "uninstall",
            },
            "com.triada.system": {
                "description": "Triada Trojan — one of the most advanced Android trojans, modifies Zygote process for root-level persistence.",
                "category": "Rootkit",
                "solution": "Factory reset and reflash stock firmware. This malware survives normal resets in some cases.",
                "fix_action": "uninstall",
            },
            "com.xhelper.dropper": {
                "description": "xHelper dropper — reinstalls itself even after factory reset by hiding in system partition.",
                "category": "Persistent Dropper",
                "solution": "Flash official stock ROM. Factory reset alone is insufficient for this malware.",
                "fix_action": "uninstall",
            },
        }

        # ------------------------------------------------------------------ #
        #  Permission risk weights (higher = more dangerous)
        # ------------------------------------------------------------------ #
        self.permission_risks = {
            "android.permission.READ_SMS":               20,
            "android.permission.SEND_SMS":               30,
            "android.permission.RECEIVE_SMS":            30,
            "android.permission.RECORD_AUDIO":           25,
            "android.permission.ACCESS_FINE_LOCATION":   15,
            "android.permission.READ_CONTACTS":          10,
            "android.permission.WRITE_CONTACTS":         15,
            "android.permission.CAMERA":                 20,
            "android.permission.SYSTEM_ALERT_WINDOW":    40,
            "android.permission.BIND_DEVICE_ADMIN":      50,
            "android.permission.PROCESS_OUTGOING_CALLS": 25,
            "android.permission.READ_CALL_LOG":          20,
            "android.permission.WRITE_CALL_LOG":         25,
            "android.permission.GET_ACCOUNTS":           15,
            "android.permission.USE_CREDENTIALS":        20,
            "android.permission.MANAGE_ACCOUNTS":        20,
            "android.permission.INSTALL_PACKAGES":       45,
            "android.permission.DELETE_PACKAGES":        40,
            "android.permission.RECEIVE_BOOT_COMPLETED": 10,
            "android.permission.WRITE_EXTERNAL_STORAGE": 10,
            "android.permission.CHANGE_WIFI_STATE":      15,
            "android.permission.BLUETOOTH_ADMIN":        10,
            "android.permission.CHANGE_NETWORK_STATE":   10,
            "android.permission.MOUNT_UNMOUNT_FILESYSTEMS": 20,
            "android.permission.WRITE_SETTINGS":         20,
            "android.permission.READ_PHONE_STATE":       15,
        }

    # ---------------------------------------------------------------------- #

    def analyze_package(self, package_name, permissions):
        threats = []
        score = 0

        # 1. Signature match
        if package_name in self.signature_blacklist:
            info = self.signature_blacklist[package_name]
            threats.append({
                "type":       f"Malware Signature — {info['category']}",
                "risk":       "CRITICAL",
                "description": info["description"],
                "solution":   info["solution"],
                "fix_action": info["fix_action"],
                "package":    package_name,
            })
            score += 100

        # 2. Heuristic permission analysis
        perm_score = 0
        flagged = []
        for perm in permissions:
            if perm in self.permission_risks:
                perm_score += self.permission_risks[perm]
                flagged.append(perm.replace("android.permission.", ""))

        has_sms     = any("SMS"      in p for p in permissions)
        has_internet = "android.permission.INTERNET" in permissions
        has_mic     = "android.permission.RECORD_AUDIO"       in permissions
        has_loc     = "android.permission.ACCESS_FINE_LOCATION" in permissions
        has_contacts = "android.permission.READ_CONTACTS"     in permissions
        has_install = "android.permission.INSTALL_PACKAGES"   in permissions
        has_admin   = "android.permission.BIND_DEVICE_ADMIN"  in permissions
        has_calllog = "android.permission.READ_CALL_LOG"       in permissions

        # SMS + Internet → spyware / premium dialer
        if has_sms and has_internet:
            perm_score += 20
            flagged.append("SMS+Internet Combo")

        # Mic + Location + Contacts → surveillance combo
        if has_mic and has_loc and has_contacts:
            perm_score += 30
            flagged.append("Surveillance Combo (Mic+GPS+Contacts)")

        # Install + Internet → dropper / downloader
        if has_install and has_internet:
            perm_score += 35
            flagged.append("Dropper Behavior (Install+Internet)")

        # Device admin → ransomware / persistence
        if has_admin:
            perm_score += 40
            flagged.append("Device Admin — Ransomware Risk")

        # Call log + Contacts + Internet → stalkerware
        if has_calllog and has_contacts and has_internet:
            perm_score += 25
            flagged.append("Stalkerware Pattern (CallLog+Contacts+Internet)")

        # Map score to severity
        if perm_score >= 80:
            level = "HIGH"
            solution = (
                f"This app has an extremely suspicious permission set. "
                f"Go to Settings › Apps › find this app › Permissions and revoke "
                f"READ_SMS, RECORD_AUDIO, ACCESS_FINE_LOCATION. "
                f"If the app has no legitimate reason for these permissions, uninstall it."
            )
            fix_action = "review_permissions"
        elif perm_score >= 50:
            level = "MEDIUM"
            solution = (
                f"Excessive permissions detected. Open Settings › Apps, find this app, "
                f"tap Permissions and disable any permission it doesn't genuinely need."
            )
            fix_action = "review_permissions"
        elif perm_score >= 25:
            level = "LOW"
            solution = (
                f"Low-risk permissions present. Monitor app behavior and restrict "
                f"background data in Settings › Apps › Mobile Data if concerned."
            )
            fix_action = "review_permissions"
        else:
            level = None

        if level:
            threats.append({
                "type":       "Heuristic Detection" if level == "HIGH" else "Permission Warning",
                "risk":       level,
                "description": f"Suspicious permissions: {', '.join(flagged[:5])}",
                "solution":   solution,
                "fix_action": fix_action,
                "package":    package_name,
            })

        return threats, min(perm_score + score, 100)

    def calculate_device_risk(self, app_scans):
        if not app_scans:
            return 0
        scores   = [s["score"] for s in app_scans]
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        return min((max_score * 0.7) + (avg_score * 0.3), 100)
