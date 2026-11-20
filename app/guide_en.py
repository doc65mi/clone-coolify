"""English setup guide. Commands are shared with the Italian version."""
SECTIONS = [
    {'title': 'Choose where to run the app', 'text':
     'Use a computer or management server that can reach both instances. Do not install the worker among the source applications that will be stopped, or on the destination that must remain empty. You can configure access later.',
     'items': ['Source: the server whose applications you want to copy.',
               'Destination: another Coolify server without applications or databases that need to be preserved.',
               'This release requires one managed Docker Linux server per instance, matching Coolify versions and the same CPU architecture.']},
    {'title': 'Prepare Coolify URLs and API tokens', 'text':
     'Open each Coolify dashboard, enable API access if necessary and create a token under Keys & Tokens / API tokens. Labels may vary by version. Use tokens with full resource visibility, not restricted to individual projects.',
     'items': ['Source: read and read:sensitive permissions, needed for environment variables and database credentials.',
               'Destination: also write and deploy permissions to create and prepare resources.',
               'In Connections, enter the base URL, such as https://coolify.example.com, and its token. Do not put the token in the URL.',
               'Use HTTPS with a valid certificate. HTTP is an explicit option for a trusted network.',
               'You do not need to share addresses in chat: tokens are stored encrypted on the backend.']},
    {'title': 'Prepare SSH keys', 'text':
     'Place one private key per server in the installation’s ssh directory. Use dedicated keys that are already authorized or create them on the management computer. The worker cannot handle passphrase or SSH password prompts.',
     'commands': ['ssh-keygen -t ed25519 -f ./ssh/source_ed25519', 'ssh-keygen -t ed25519 -f ./ssh/target_ed25519'],
     'items': ['These commands are optional: do not overwrite existing keys. Leave the passphrase empty for worker keys and protect access to the files.',
               'Install the matching .pub file contents in ~/.ssh/authorized_keys for the user on the correct server; use the provider’s administrative console or an already verified connection.',
               'Private keys stay on the management computer. Do not copy them to the servers or paste them into token fields.',
               'In Docker, ./ssh is mounted read-only at /ssh. On Linux, keys must have permissions 600 and be readable by UID 10001.',
               'Enter the host, port, user and filename in the forms. For a non-root user, enable sudo and configure non-interactive sudo for the required operations.']},
    {'title': 'Verify host identities and prerequisites', 'text':
     'Create ssh/known_hosts with the hosts’ public keys. Compare fingerprints using the provider console or an already verified channel. Collecting keys with ssh-keyscan alone does not authenticate the server.',
     'items': ['For an SSH port other than 22, known_hosts must contain the host in [host]:port format.',
               'Each server needs Docker CLI, Python 3.8+ and GNU tar with ACL and xattr support. Databases need their native dump and restore tools.',
               'API and SSH must reach the same host. External proxies on different IP addresses and multi-server instances are not supported in this release.',
               'The status checks here only verify local file presence. SSH access, permissions and host identities are checked during Analyze selection.']},
    {'title': 'Save connections and analyze', 'text':
     'Open Connections and complete both cards. If Coolify manages one server, its UUID is selected automatically. To update connections, enter both tokens again: stored tokens are not displayed.',
     'items': ['Save connections does not contact or modify the servers.',
               'In Overview, choose Load source resources and select applications: databases with recognized references appear below their app and are included automatically.',
               'Shared databases remain selected while a chosen app requires them. Internal stack databases are included with their stack; databases without a verified link remain separate and can be selected manually.',
               'Analyze selection reads API and Docker information via SSH without remote changes. Excluded resources are neither created nor stopped.',
               'The plan lists resources and blockers. You cannot start a copy if a resource needs an unavailable adapter.',
               'Regenerate the plan after server or option changes; it expires after 15 minutes.']},
    {'title': 'Run the copy and verify the result', 'text':
     'When the plan is ready, schedule downtime and suspend deployments, cron jobs and external writers. Verify enough free space for all data on both the management computer and destination.',
     'items': ['Confirm the plan: source applications stop while encrypted backups are acquired and are then restarted.',
               'Use Operations to follow progress, event logs, backup checksums and exportable reports.',
               'The destination stays stopped. Check databases, variables and mounts before starting it in Coolify.',
               'The clone is a snapshot at backup time. Later source writes are not replicated; DNS changes, activation and final synchronization are not automatic.',
               'After an interruption, check the source. Recover source is available in Operations; if the network is unavailable, intervene through the console or SSH.']}
]
LIMITS = [
    'Available: compatible Docker Image applications, GitHub App applications using Dockerfile builds, readable variables, verifiable named volumes, and PostgreSQL/MySQL/MariaDB with one application database and supported users.',
    'Blocked: other Git sources/build packs, Services/Compose stacks, bind/file mounts, shared or locked variables, unsupported advanced settings, public databases, multiple databases/roles and other engines.',
    'Not copied: Coolify users and global settings, cron jobs, registries, scheduled backups and external services. No automatic DNS changes. Required GitHub credentials are imported for supported applications; auto deploy and previews are disabled on the copy.',
    'A full clone has not yet been tested end-to-end on real instances: first run a trial on two disposable test instances.'
]
