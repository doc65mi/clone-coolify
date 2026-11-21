"""Read-only onboarding content and local prerequisites. Never reads SSH key contents."""
from pathlib import Path
from .guide_en import SECTIONS as EN_SECTIONS, LIMITS as EN_LIMITS

SECTIONS = [
    {"title": "Scegli dove eseguire l'app", "text":
     "Usa un computer o un server di gestione che raggiunga entrambe le istanze. Non installare il worker fra le applicazioni da fermare sulla sorgente o sulla destinazione che deve risultare vuota. Puoi configurare tutti gli accessi in seguito.",
     "items": ["Sorgente: server dal quale copiare le applicazioni.",
               "Destinazione: altro server Coolify, privo di applicazioni e database da conservare.",
               "La release richiede un solo server Docker Linux gestito per istanza, stessa versione Coolify e stessa architettura CPU."]},
    {"title": "Prepara URL e token API Coolify", "text":
     "Apri ciascuna dashboard Coolify, abilita l'accesso API se necessario e crea un token dalla sezione Keys & Tokens / API tokens. I nomi delle voci possono variare con la versione. Usa token con visibilità completa, non limitati a singoli progetti.",
     "items": ["Sorgente: permessi di lettura e lettura dei dati sensibili, necessari per variabili e credenziali database.",
               "Destinazione: anche permessi di scrittura e deploy per creare e preparare le risorse.",
               "In Connessioni inserisci l'URL base, per esempio https://coolify.example.it, e il relativo token. Non mettere il token nell'URL.",
               "Usa HTTPS con certificato valido. HTTP è un'opzione esplicita per una rete fidata.",
               "Non serve inserire gli indirizzi in chat: i token vengono salvati cifrati nel backend."]},
    {"title": "Prepara le chiavi SSH", "text":
     "Nella cartella ssh dell'installazione inserisci una chiave privata per ogni server. Puoi usare chiavi dedicate già autorizzate oppure crearle sul computer di gestione. Il worker non gestisce prompt di passphrase o password SSH.",
     "commands": ["ssh-keygen -t ed25519 -f ./ssh/source_ed25519", "ssh-keygen -t ed25519 -f ./ssh/target_ed25519"],
     "items": ["I comandi sono facoltativi: non sovrascrivere chiavi già esistenti. Per chiavi dedicate al worker lascia vuota la passphrase e proteggi l'accesso ai file.",
               "Installa il contenuto del relativo file .pub in ~/.ssh/authorized_keys dell'utente sul server corretto; usa la console amministrativa del provider o un accesso già verificato.",
               "I file privati restano sul computer di gestione. Non copiarli sui server né inserirli nei campi token.",
               "Su Docker la directory ./ssh viene montata in /ssh in sola lettura. Su Linux le chiavi devono avere permessi 600 ed essere leggibili dall'UID 10001.",
               "Indica host, porta, utente e nome file nei moduli. Se l'utente non è root, abilita sudo e predisponi sudo non interattivo per le operazioni richieste."]},
    {"title": "Verifica le identità host e i prerequisiti", "text":
     "Crea ssh/known_hosts con le chiavi pubbliche degli host. Confronta le impronte con la console del provider o con un canale già verificato. La sola raccolta con ssh-keyscan non autentica il server.",
     "items": ["Per una porta SSH diversa da 22, known_hosts deve contenere il nome nella forma [host]:porta.",
               "Ogni server richiede Docker CLI, Python 3.8+ e GNU tar con supporto ACL e xattrs. I database richiedono i relativi strumenti di dump e ripristino.",
               "API e SSH devono raggiungere lo stesso host. Proxy esterni su IP differenti e istanze multi-server non sono supportati in questa release.",
               "Il controllo qui sotto verifica solo la presenza locale dei file. Accesso SSH, autorizzazioni e impronte vengono verificati durante Analizza selezione."]},
    {"title": "Salva i server e scegli i ruoli", "text":
     "In Connessioni aggiungi o modifica un server salvato con URL, token API e SSH. Lascia vuoto il token di un profilo esistente per conservarlo. In Panoramica scegli trasmittente e ricevente nell’elenco, una riga per server, e premi Applica ruoli. Non devi reinserire le credenziali per scegliere i ruoli.",
     "items": ["Salva server e Applica ruoli salvano impostazioni locali: non contattano e non modificano i server.",
               "Nella Panoramica usa Carica elenco sorgente e spunta le applicazioni da copiare: i database con un riferimento riconosciuto vengono mostrati sotto l'app e inclusi automaticamente.",
               "I database condivisi restano selezionati finché richiesti da un'app scelta. Quelli interni agli stack sono inclusi con lo stack; quelli senza collegamento verificato restano separati e selezionabili manualmente.",
               "Analizza selezione legge API e Docker via SSH, senza modifiche remote. Le risorse escluse non vengono create né fermate.",
               "Il piano elenca risorse e blocchi. Non è possibile avviare una copia se una risorsa richiede un adattatore non disponibile.",
               "Dopo ogni modifica ai server o alle opzioni rigenera il piano; scade dopo 15 minuti."]},
    {"title": "Esegui la copia e controlla il risultato", "text":
     "Quando il piano è pronto, pianifica il fermo e sospendi deploy, cron e scrittori esterni. Verifica spazio libero per tutti i dati sia sul computer di gestione sia sulla destinazione.",
     "items": ["Conferma il piano: le applicazioni sorgente si fermano durante l'acquisizione dei backup cifrati, poi vengono riavviate.",
               "Segui Operazioni per avanzamento, registro eventi, checksum dei backup e report esportabile.",
               "La destinazione resta ferma. Verifica database, variabili e mount prima dell'avvio in Coolify.",
               "Il clone rappresenta l'istante del backup. Le scritture successive sulla sorgente non vengono replicate; DNS, attivazione e sincronizzazione finale non sono automatici.",
               "Dopo un'interruzione controlla la sorgente. In Operazioni è disponibile Recupera sorgente; se manca la rete, intervieni tramite console o SSH."]},
]

LIMITS = [
    "Disponibili: applicazioni Docker Image compatibili, GitHub App con build Dockerfile, variabili leggibili, volumi nominati verificabili e database PostgreSQL/MySQL/MariaDB con un database applicativo e utenti supportati.",
    "Bloccati: altre sorgenti Git/build pack, stack Services/Compose, bind/file mount, variabili condivise o bloccate, configurazioni avanzate non supportate, database pubblici o con più database/ruoli e altri motori.",
    "Non copiati: utenti e impostazioni globali Coolify, cron, registry, backup pianificati e servizi esterni. Nessuna modifica automatica ai DNS. Le credenziali GitHub necessarie vengono importate per le app supportate; auto deploy e anteprime disattivati sulla copia.",
    "Nessuna clonazione è stata ancora collaudata su istanze reali: esegui prima una prova su due istanze di test.",
]


def setup_status(configs, directory, version, language='it'):
    root = Path(directory)
    checks = []
    for role in ("source", "target"):
        config = (configs or {}).get(role) or {}
        filename = config.get("ssh_key") or f"{role}_ed25519"
        # Config is validated on write. Avoid traversing even if its persisted value is damaged.
        safe = Path(filename).name == filename and ".." not in filename
        checks.append({"role": role, "configured": bool(config), "key_name": filename if safe else "Nome non valido",
                       "key_present": bool(safe and (root / filename).is_file())})
    return {"version": version, "ssh_directory": str(root), "known_hosts_present": (root / "known_hosts").is_file(),
            "connections": checks, "sections": EN_SECTIONS if language == 'en' else SECTIONS,
            "limits": EN_LIMITS if language == 'en' else LIMITS}
