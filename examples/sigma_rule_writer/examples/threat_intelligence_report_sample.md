# Sigma Rule Writer Output Example

## Input

**Type**: Threat Intelligence Report URL

**Content**:
```
Here is a threat intelligence report describing attack techniques currently used by hackers:
https://www.anthropic.com/threat-intelligence-report-september-2026
```

## Processing

The system automatically:
1. Read the threat intelligence URL
2. Extracted 5 distinct attack techniques
3. Researched current threat intelligence for each technique
4. Generated a Sigma rule per technique
5. Validated all rules successfully

## Techniques Identified

| # | Technique | Description | Level |
|---|-----------|-------------|-------|
| 1 | AI-Driven Malware Evasion & Staging | Scripting engine spawning LOLBin/downloader with network URL | Medium |
| 2 | Device Code Phishing / Embassy Kit | OAuth 2.0 device code flow abused for token theft (Midnight Blizzard) | High |
| 3 | CaptiveCrunch ClickFix Delivery | User tricked into pasting malicious command via Windows Run dialog | High |
| 4 | WhatsApp Takeover via WPPConnect | Headless Chrome automation for WhatsApp account hijacking | High |
| 5 | Embassy Kit M365 Email Exfiltration | Bulk email collection via Graph API post-authentication | High |

## Generated Sigma Rules

### Rule 1: Malware Staging via Disposable Hosting with Obfuscated Dropper Execution

```yaml
title: Malware Staging via Disposable Hosting with Obfuscated Dropper Execution
id: a3f7c2e1-84b5-4d9a-b6f3-2e1c9d0a7f45
status: experimental
description: |
  Detects potential AI-assisted malware staging behavior where a small dropper process
  spawns a scripting engine or LOLBin that downloads and executes a payload from the
  network. This pattern is consistent with automated malware redeployment workflows
  where AI agents iteratively rebuild and stage malware on disposable hosting servers
  until it evades detection.
references:
  - https://attack.mitre.org/techniques/T1027/
  - https://attack.mitre.org/techniques/T1105/
author: Detection Engineering
date: 2026-09-01
tags:
  - attack.defense-evasion
  - attack.t1027
  - attack.t1027.002
  - attack.t1105
  - attack.t1055
logsource:
  category: process_creation
  product: windows
detection:
  selection_parent:
    ParentImage|endswith:
      - '\cmd.exe'
      - '\powershell.exe'
      - '\wscript.exe'
      - '\cscript.exe'
      - '\mshta.exe'
      - '\rundll32.exe'
  selection_child:
    Image|endswith:
      - '\powershell.exe'
      - '\cmd.exe'
      - '\msiexec.exe'
      - '\certutil.exe'
      - '\bitsadmin.exe'
      - '\curl.exe'
      - '\wscript.exe'
      - '\cscript.exe'
  selection_download:
    CommandLine|contains:
      - 'http://'
      - 'https://'
      - 'DownloadFile'
      - 'DownloadString'
      - 'WebClient'
      - 'Invoke-WebRequest'
      - 'iwr '
      - 'wget '
      - 'curl '
      - 'bitsadmin'
      - 'certutil -urlcache'
      - 'certutil -decode'
  filter_legitimate:
    CommandLine|contains:
      - 'windowsupdate.com'
      - 'microsoft.com/updates'
      - 'download.microsoft.com'
  condition: selection_parent and selection_child and selection_download and not filter_legitimate
falsepositives:
  - Legitimate software installers that download components during installation
  - IT administration scripts that download tools from internal servers
  - Software update mechanisms
level: medium
```

### Rule 2: Azure AD Device Code Authentication Flow Detected

```yaml
title: Azure AD Device Code Authentication Flow Detected
id: b8e4d1f2-93c6-4e7b-a5d2-3f2b0e1c8a67
status: experimental
description: |
  Detects sign-in events using the OAuth 2.0 device authorization grant (device code flow)
  in Azure Active Directory / Entra ID. Device code phishing abuses this legitimate flow
  to steal Microsoft 365 OAuth tokens: the attacker initiates the flow, sends the user code
  to the victim via phishing, and collects the resulting access and refresh tokens when the
  victim authenticates. This technique is used by threat actors including Storm-2372 and
  the Embassy Kit framework attributed to Midnight Blizzard (GTG-20006).
references:
  - https://attack.mitre.org/techniques/T1528/
  - https://attack.mitre.org/techniques/T1566/002/
  - https://www.microsoft.com/en-us/security/blog/2025/02/13/storm-2372-conducts-device-code-phishing-campaign/
author: Detection Engineering
date: 2026-09-01
tags:
  - attack.credential-access
  - attack.initial-access
  - attack.t1528
  - attack.t1566.002
logsource:
  product: azure
  service: signinlogs
detection:
  selection:
    AuthenticationProtocol: deviceCode
    ResultType: '0'
  filter_known_apps:
    AppId:
      - '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
      - '1950a258-227b-4e31-a9cf-717495945fc2'
  condition: selection and not filter_known_apps
falsepositives:
  - Legitimate use of Azure CLI or Azure PowerShell by administrators in environments
    where device code flow is an approved authentication method
  - IoT or headless device provisioning workflows
level: high
```

### Rule 3: ClickFix Malware Execution via Windows Run Dialog

```yaml
title: ClickFix Malware Execution via Windows Run Dialog
id: c9f5e2a3-74d7-4f8c-b6e3-4a3c1f2d9b78
status: experimental
description: |
  Detects ClickFix-style malware delivery where a victim is socially engineered into
  pasting a malicious command into the Windows Run dialog (Win+R), resulting in
  explorer.exe spawning a scripting engine or LOLBin. This technique is used in
  DNS hijacking campaigns (CaptiveCrunch/Storm-2945) where hotel guest WiFi traffic
  is redirected to attacker-controlled servers that serve fake CAPTCHA pages.
  The RunMRU registry key records commands entered in the Run dialog and is a
  reliable forensic artifact.
references:
  - https://attack.mitre.org/techniques/T1204/001/
  - https://attack.mitre.org/techniques/T1059/001/
  - https://attack.mitre.org/techniques/T1218/007/
author: Detection Engineering
date: 2026-09-01
tags:
  - attack.execution
  - attack.initial-access
  - attack.t1204.001
  - attack.t1059.001
  - attack.t1218.007
  - attack.t1218.005
logsource:
  category: process_creation
  product: windows
detection:
  selection_parent:
    ParentImage|endswith: '\explorer.exe'
  selection_child:
    Image|endswith:
      - '\powershell.exe'
      - '\cmd.exe'
      - '\mshta.exe'
      - '\msiexec.exe'
      - '\wscript.exe'
      - '\cscript.exe'
  selection_suspicious_cmd:
    CommandLine|contains:
      - 'http://'
      - 'https://'
      - 'DownloadFile'
      - 'DownloadString'
      - 'Invoke-WebRequest'
      - 'iwr '
      - 'IEX'
      - 'Invoke-Expression'
      - '-enc '
      - '-EncodedCommand'
      - '/i http'
      - 'msiexec'
      - 'certutil'
  filter_legitimate:
    CommandLine|contains:
      - 'C:\Windows\system32'
      - 'C:\Program Files'
  condition: selection_parent and selection_child and selection_suspicious_cmd and not filter_legitimate
falsepositives:
  - Legitimate administrative tasks run from the Run dialog
  - Software installation initiated by users from the Run dialog
level: high
```

### Rule 4: Headless Chrome Spawned by Scripting Engine for WhatsApp Automation

```yaml
title: Headless Chrome Spawned by Scripting Engine for WhatsApp Automation
id: d1a6f3b4-85e8-4a9d-c7f4-5b4d2a3e0c89
status: experimental
description: |
  Detects headless Chrome or Chromium browser processes spawned by scripting engines
  (Python, PowerShell, cmd) with automation flags consistent with WPPConnect or
  Selenium-based WhatsApp account takeover. Threat actors use this technique to link
  victim WhatsApp accounts as companion devices, suppress read receipts, and bulk-export
  conversations. This pattern was observed in campaigns targeting Ukrainian government
  officials attributed to Russian state-sponsored actors (GTG-20006/Midnight Blizzard).
references:
  - https://attack.mitre.org/techniques/T1528/
  - https://attack.mitre.org/techniques/T1119/
  - https://github.com/wppconnect-team/wppconnect
author: Detection Engineering
date: 2026-09-01
tags:
  - attack.collection
  - attack.credential-access
  - attack.t1528
  - attack.t1119
  - attack.t1555
logsource:
  category: process_creation
  product: windows
detection:
  selection_parent:
    ParentImage|endswith:
      - '\python.exe'
      - '\python3.exe'
      - '\powershell.exe'
      - '\cmd.exe'
      - '\wscript.exe'
      - '\cscript.exe'
  selection_browser:
    Image|endswith:
      - '\chrome.exe'
      - '\chromium.exe'
      - '\msedge.exe'
  selection_headless_flags:
    CommandLine|contains:
      - '--headless'
  selection_automation_flags:
    CommandLine|contains:
      - '--remote-debugging-port'
      - '--disable-blink-features=AutomationControlled'
      - '--user-data-dir'
      - 'whatsapp'
      - 'web.whatsapp.com'
  condition: selection_parent and selection_browser and selection_headless_flags and selection_automation_flags
falsepositives:
  - Legitimate automated testing frameworks using headless Chrome for web testing
  - CI/CD pipelines running browser-based tests
  - Legitimate WhatsApp Business API integrations
level: high
```

### Rule 5: Microsoft 365 Bulk Email Collection via Graph API After Device Code Authentication

```yaml
title: Microsoft 365 Bulk Email Collection via Graph API After Device Code Authentication
id: e2b7a4c5-96f9-4b0e-d8a5-6c5e3b4f1d90
status: experimental
description: |
  Detects bulk email collection from Microsoft 365 mailboxes via the Microsoft Graph API
  following device code authentication. After stealing OAuth tokens via device code phishing
  (Embassy Kit framework), threat actors enumerate mail folders and bulk-retrieve messages
  using the Graph API. This technique was used by GTG-20006 (Midnight Blizzard) to exfiltrate
  email from government, military, and intergovernmental organizations.
references:
  - https://attack.mitre.org/techniques/T1114/002/
  - https://attack.mitre.org/techniques/T1528/
  - https://learn.microsoft.com/en-us/microsoft-365/compliance/audit-mailitemsaccessed
author: Detection Engineering
date: 2026-09-01
tags:
  - attack.collection
  - attack.exfiltration
  - attack.t1114.002
  - attack.t1528
  - attack.t1530
logsource:
  product: m365
  service: threat_management
detection:
  selection:
    eventSource: SecurityComplianceCenter
    Operation:
      - MailItemsAccessed
      - MailboxLogin
  selection_anomalous:
    ClientInfoString|contains:
      - 'Client=REST'
      - 'Client=Graph'
      - 'curl'
      - 'python'
      - 'PowerShell'
  condition: selection and selection_anomalous
falsepositives:
  - Legitimate third-party email archiving or backup solutions using Graph API
  - Authorized email migration tools
  - Legitimate compliance or eDiscovery tools
level: high
```

## Key Observations

1. **Multi-Technique Processing**: System extracted 5 distinct techniques from one threat intelligence URL
2. **Diverse Log Sources**: Rules span Windows process creation, Azure AD, and Microsoft 365
3. **Real-World Threat Attribution**: References actual threat actors (Midnight Blizzard, Storm-2372, CaptiveCrunch)
4. **Production Quality**: All rules validate successfully and convert to actual SIEM queries
5. **Proper Sigma Syntax**: Correct use of modifiers, conditions, filtering, and MITRE ATT&CK tagging

## Validation Status

All 5 rules passed sigma_validate checks including:
- YAML syntax validation
- Sigma field taxonomy compliance
- Detection logic review
