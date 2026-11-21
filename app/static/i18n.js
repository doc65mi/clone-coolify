'use strict';
// User data is never passed through this catalogue. Placeholders preserve names and values.
const CloneI18n = (() => {
  const en = {
    'Un nuovo server.':'A new server.', 'Lo stesso progetto.':'The same project.',
    'Accedi per collegare le istanze e preparare una copia verificata dei tuoi dati.':'Sign in to connect your instances and prepare a verified copy of your data.',
    'Password amministratore':'Administrator password', 'Accedi al workspace':'Sign in to workspace',
    "La password iniziale è nel file .env dell'installazione.":'The initial password is in the installation’s .env file.',
    'Navigazione principale':'Main navigation', 'Panoramica':'Overview', 'Connessioni':'Connections',
    'Guida e istruzioni':'Setup guide', 'Operazioni':'Operations', 'Copia i tuoi progetti.':'Copy your projects.',
    'Mantieni il controllo.':'Stay in control.', 'Esci dal workspace':'Sign out', 'Sessione privata':'Private session',
    'Puoi collegare i server quando vuoi.':'Connect your servers whenever you are ready.',
    'Le istruzioni per URL, token API e chiavi SSH sono già disponibili nel backend.':'Instructions for URLs, API tokens and SSH keys are already available here.',
    'Apri la guida alla configurazione':'Open setup guide', 'Porta tutto al prossimo server.':'Move your projects to the next server.',
    'Collega, verifica e prepara il clone. Un passaggio alla volta, con ogni operazione tracciata.':'Connect, verify and prepare your clone. One step at a time, with every operation logged.',
    'Configura connessioni':'Set up connections', 'SORGENTE':'SOURCE', 'DESTINAZIONE':'DESTINATION',
    'Da dove partiamo':'Where we start', 'Dove andiamo':'Where we go', 'Istanza non collegata':'Instance not connected',
    'In attesa di configurazione':'Awaiting configuration', 'COPIA':'COPY', 'Destinazione vuota richiesta':'Empty destination required',
    'Risorse rilevate':'Resources found', 'Applicazioni e database nel piano':'Applications and databases in the plan',
    'Volumi applicativi':'Application volumes', 'File persistenti da trasferire':'Persistent files to transfer',
    'Controlli da risolvere':'Checks requiring attention', 'Devono essere zero per procedere':'Must be zero to proceed',
    'Scegli cosa clonare':'Choose what to clone',
    "Seleziona un'applicazione: i suoi database collegati vengono inclusi automaticamente.":'Select an application: its linked databases are included automatically.',
    'Carica elenco sorgente':'Load source resources', 'Nessuna risorsa selezionata':'No resources selected',
    'Seleziona tutte':'Select all', 'Deseleziona tutte':'Deselect all',
    "Puoi inserire gli indirizzi in seguito in Connessioni. L'elenco verrà caricato solo quando lo richiedi.":'You can enter the addresses later in Connections. The list is loaded only when you request it.',
    'Scegli':'Select', 'Risorsa':'Resource', 'Tipo':'Type', 'Progetto / ambiente':'Project / environment',
    "I database sono raggruppati sotto le applicazioni tramite i riferimenti riconosciuti nella configurazione. Quelli condivisi restano selezionati finché richiesti da un'app scelta. I database senza collegamento verificato sono elencati separatamente. La destinazione deve essere vuota.":'Databases are grouped below applications using recognized configuration references. Shared databases remain selected while a chosen app requires them. Databases without a verified link are listed separately. The destination must be empty.',
    'Piano di clonazione':'Cloning plan', "L'analisi controlla le risorse selezionate senza modificarle.":'Analysis checks the selected resources without changing them.',
    'Analizza selezione':'Analyze selection', 'Mantieni i domini originali nelle configurazioni (DNS invariati)':'Keep original domains in configurations (DNS unchanged)',
    'Prima conosciamo i tuoi server.':'First, let’s check your servers.', "Configura le connessioni e avvia l'analisi.":'Set up your connections and start the analysis.',
    'Qui vedrai le risorse e gli eventuali ostacoli.':'Your resources and any blockers will appear here.', 'Dati':'Data', 'Esito':'Result',
    'COME FUNZIONA':'HOW IT WORKS', 'Dal piano alla copia.':'From plan to copy.', 'Verifica':'Verify',
    'Identità, versioni, risorse e destinazione vuota.':'Identity, versions, resources and an empty destination.',
    'Proteggi i dati':'Protect your data', 'Fermo applicazioni e backup cifrati con verifica di integrità.':'Application downtime and encrypted backups with integrity checks.',
    'Ricrea e ripristina':'Recreate and restore', 'Nuove risorse, variabili e dati sulla destinazione.':'New resources, variables and data on the destination.',
    'Controlla il risultato':'Check the result', 'Sorgente riavviata. Destinazione ferma per la verifica finale.':'Source restarted. Destination stopped for final verification.',
    'Prepara la clonazione':'Prepare cloning', 'Il piano è valido per 15 minuti.':'The plan is valid for 15 minutes.',
    'Due istanze. Un collegamento.':'Two instances. One connection.',
    'I token restano sul backend, cifrati. Le chiavi private si montano come file in sola lettura.':'Tokens stay encrypted on the backend. Private keys are mounted as read-only files.',
    'Leggi le istruzioni per configurare i server':'Read server setup instructions', 'Prima di collegare i server':'Before connecting your servers',
    'Usa token con visibilità completa sulle risorse: lettura e dati sensibili sulla sorgente, anche scrittura e deploy sulla destinazione. Nella cartella':'Use tokens with full resource visibility: read and sensitive data on the source, plus write and deploy on the destination. In the',
    'inserisci le chiavi e il file':'directory, place the keys and the file',
    ', dopo aver verificato le impronte SSH. Non usare il clone su uno dei workload da fermare.':', after verifying SSH fingerprints. Do not run this app on a workload that will be stopped.',
    'Per modificare le connessioni, reinserisci entrambi i token.':'To change connections, enter both tokens again.', 'Salva connessioni':'Save connections',
    'Ogni passaggio, visibile.':'Every step, visible.', 'Stato delle copie, backup e recupero della sorgente.':'Copy status, backups and source recovery.',
    'Aggiorna':'Refresh', 'CONFIGURAZIONE GUIDATA':'GUIDED SETUP', 'Tutto pronto, quando lo sei tu.':'Ready when you are.',
    'Prepara gli accessi e collega i server in seguito. Consultare questa guida non contatta i server.':'Prepare access and connect your servers later. Viewing this guide does not contact the servers.',
    'Aggiorna stato locale':'Refresh local status', 'Stato della configurazione':'Configuration status',
    'Presenza dei file e connessioni salvate. Non è un test di accesso ai server.':'Local file presence and saved connections. This is not a server access test.',
    'Supporto e limiti della versione':'Release support and limitations',
    'Gli indirizzi possono essere inseriti quando sei pronto. Nessun token viene richiesto in chat.':'Enter the addresses when you are ready. No tokens are requested in chat.',
    'Configura i server':'Configure servers', 'Clone Coolify / Un workspace indipendente':'Clone Coolify / An independent workspace',
    'Nessuna modifica automatica ai DNS':'No automatic DNS changes', 'AVVIO DELLA COPIA':'START COPYING',
    'Conferma il piano verificato.':'Confirm the verified plan.',
    'Le applicazioni sorgente saranno fermate per acquisire il backup, poi riavviate. Il risultato sulla destinazione resterà fermo.':'Source applications will be stopped for backup acquisition, then restarted. The destination copy will remain stopped.',
    'Accetto il fermo temporaneo delle applicazioni sorgente.':'I accept temporary downtime for source applications.',
    'Ho sospeso client esterni, cron e altre scritture ai database durante il backup.':'I have suspended external clients, cron jobs and other database writers during the backup.',
    'Scrivi CLONA DESTINAZIONE VUOTA':'Type CLONA DESTINAZIONE VUOTA',
    'Le operazioni fallite non vengono ritentate o cancellate automaticamente. I backup vengono conservati.':'Failed operations are not retried or deleted automatically. Backups are retained.',
    'Annulla':'Cancel', 'Avvia clonazione':'Start cloning', 'Lingua':'Language',
    'PostgreSQL e GitHub/Dockerfile supportati nelle configurazioni compatibili. Analizza sempre la selezione prima della copia.':'PostgreSQL and GitHub/Dockerfile are supported in compatible configurations. Always analyze the selection before copying.',
    'Risposta del server non valida':'Invalid server response', 'Sessione scaduta: accedi nuovamente':'Session expired: please sign in again',
    'Operazione non riuscita':'Operation failed', 'Il server da copiare':'The server to copy', 'Il nuovo server':'The new server',
    'URL Coolify':'Coolify URL', 'Token API':'API token', 'Token con visibilità completa':'Token with full resource visibility',
    'UUID server Coolify (facoltativo)':'Coolify server UUID (optional)', 'Automatico se è presente un solo server':'Automatic when only one server exists',
    'IP o hostname SSH':'SSH IP or hostname', 'Porta SSH':'SSH port', 'Utente SSH':'SSH user', 'Nome del file chiave in ssh/':'Key filename in ssh/',
    'Usa sudo non interattivo per i comandi remoti':'Use non-interactive sudo for remote commands',
    'Consenti API HTTP su rete fidata (token non cifrato in transito)':'Allow HTTP API on a trusted network (token not encrypted in transit)',
    'Configurata · da verificare':'Configured · not yet verified', 'Cartella SSH del backend: {path}':'Backend SSH directory: {path}',
    'Presente':'Present', 'Da preparare':'To be prepared', 'Sorgente':'Source', 'Destinazione':'Destination',
    '{role}: connessione salvata':'{role}: connection saved', 'File known_hosts':'known_hosts file',
    'Copia comando':'Copy command', 'Copiato':'Copied', 'Seleziona e copia il comando mostrato nella guida.':'Select and copy the command shown in the guide.',
    'Clona {name}':'Clone {name}', 'Stack Compose':'Compose stack', 'Applicazione':'Application', 'Da verificare':'Not yet verified',
    'Database di {name}':'Databases for {name}', 'Database collegati ({count})':'Linked databases ({count})',
    'Incluso automaticamente con le applicazioni selezionate':'Automatically included with selected applications', 'Selezionabile anche singolarmente':'Can also be selected separately',
    ' · Condiviso tra {count} applicazioni':' · Shared by {count} applications', '{name}: incluso nello stack {stack}':'{name}: included in stack {stack}',
    'Database interno: incluso nella selezione dello stack':'Internal database: included with the stack selection',
    'Database senza collegamento verificato':'Databases without a verified link', 'Selezione manuale: la presenza nello stesso progetto non prova un collegamento.':'Manual selection: belonging to the same project does not prove a connection.',
    '{apps} applicazioni/stack · {dbs} database selezionati':'{apps} applications/stacks · {dbs} databases selected',
    '{apps} {appLabel} · {dbs} {dbLabel}':'{apps} {appLabel} · {dbs} {dbLabel}',
    'applicazione/stack':'application/stack', 'applicazioni/stack':'applications/stacks',
    'database selezionato':'database selected', 'database selezionati':'databases selected',
    'Lettura sorgente…':'Reading source…', 'Nessuna applicazione, database o stack visibile al token sorgente.':'No applications, databases or stacks are visible to the source token.',
    'Elenco caricato. Selezionando un’app includi anche i suoi database collegati.':'List loaded. Selecting an app also includes its linked databases.',
    'Da risolvere':'Needs attention', 'Pronta':'Ready', '{volumes} vol. · {variables} var.':'{volumes} volumes · {variables} variables',
    'Analizzato alle {time}. Il piano scade dopo 15 minuti. Coolify {source} / {target}.':'Analyzed at {time}. The plan expires after 15 minutes. Coolify {source} / {target}.',
    'API e identità SSH verificate':'API and SSH identity verified', 'Pronta per la copia':'Ready for copying',
    'In coda':'Queued', 'In corso':'Running', 'Non completata':'Failed', 'Copiata · verifica finale richiesta':'Copied · final verification required',
    'Interrotta · controlla la sorgente':'Interrupted · check the source', 'Nessuna clonazione avviata':'No clones started',
    'Le operazioni appariranno qui con il loro stato e il registro degli eventi.':'Operations will appear here with their status and event log.',
    'Avanzamento clonazione':'Cloning progress', 'Fase: {phase}':'Phase: {phase}',
    'Il clone è una copia al momento del backup. La sorgente è stata riavviata; la destinazione è ferma. Avvio, verifica applicativa e passaggio DNS si eseguono in Coolify dopo aver controllato i dati.':'The clone is a snapshot taken at backup time. The source has been restarted; the destination is stopped. Start it, validate the application and switch DNS in Coolify after checking the data.',
    'Controlla subito che le applicazioni sorgente siano avviate. Un arresto del worker può impedire il recupero automatico.':'Check immediately that source applications are running. A worker shutdown may prevent automatic recovery.',
    'Nascondi registro':'Hide log', 'Mostra registro':'Show log', 'Nessun evento ancora disponibile':'No events available yet',
    'Recupera sorgente':'Recover source', 'Comando di riavvio sorgente completato.':'Source restart command completed.', 'Esporta report':'Export report',
    '{count} backup cifrati conservati':'{count} encrypted backups retained',
    'Stato locale aggiornato. Nessuna connessione ai server eseguita.':'Local status updated. No server connections were made.',
    'Connessioni salvate in forma cifrata. Ora carica l’elenco e scegli cosa clonare.':'Connections saved in encrypted form. Load the list and choose what to clone.',
    'Seleziona almeno una risorsa da clonare.':'Select at least one resource to clone.', 'Analisi in corso…':'Analyzing…',
    'Verifica API, SSH e selezione in corso. I server non vengono modificati.':'Checking API, SSH and selection. Servers are not being changed.',
    'Analisi completata: {count} controlli da risolvere.':'Analysis complete: {count} checks need attention.',
    'Analisi completata: piano pronto per la revisione.':'Analysis complete: plan ready for review.',
    'Opzioni modificate: ripeti l’analisi prima della copia.':'Options changed: analyze again before copying.',
    'Clonazione avviata. Puoi seguire l’avanzamento nel registro.':'Cloning started. Follow progress in the log.',
    'preflight':'Preflight checks', 'creazione':'Creating resources', 'fermo_sorgente':'Stopping source applications',
    'backup':'Backup', 'ripristino':'Restoring data', 'copia_completata':'Copy completed',
    'Impossibile verificare i database interni dello stack.':'Unable to verify internal stack databases.',
    'Collegamenti database non verificabili: controllare accesso API e configurazione.':'Database links could not be verified: check API access and configuration.',
    'Alcune variabili non sono leggibili: i collegamenti potrebbero essere incompleti.':'Some variables cannot be read: links may be incomplete.',
    'Adattatore Compose non disponibile':'Compose adapter unavailable', 'Da verificare nel piano':'To be checked in the plan',
    'Nome non valido':'Invalid name'
  };
  let language = 'it';
  try { language = localStorage.getItem('clone-coolify.language') === 'en' ? 'en' : 'it'; } catch {}
  const targets = [];
  const patterns = [];
  function rebuildPatterns() {
    patterns.length = 0;
    for (const [original, translated] of Object.entries(en)) {
      if (!original.includes('{')) continue;
      const names = [];
      const escaped = original.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace(/\{(\w+)\}/g, (_, name) => { names.push(name); return '(.*?)'; });
      patterns.push({regex:new RegExp('^' + escaped + '$', 's'), names, translated});
    }
  }
  function format(text, values) { return text.replace(/\{(\w+)\}/g, (all, key) => Object.hasOwn(values, key) ? String(values[key]) : all); }
  function t(text, values = {}) {
    if (typeof text !== 'string') return text;
    if (language === 'it') return format(text, values);
    if (Object.hasOwn(en, text)) return format(en[text], values);
    for (const pattern of patterns) {
      const match = text.match(pattern.regex);
      if (match) return format(pattern.translated, Object.fromEntries(pattern.names.map((name, index) => [name, match[index + 1]])));
    }
    // Plans prefix warnings with resource names. Preserve those names exactly.
    for (let index = text.indexOf(': '); index >= 0; index = text.indexOf(': ', index + 2)) {
      const suffix = text.slice(index + 2), translated = t(suffix);
      if (suffix !== translated) return text.slice(0, index + 2) + translated;
    }
    return text;
  }
  function capture(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement.closest('script,style,code,pre,option')) continue;
      const text = node.textContent.trim();
      const key = Object.hasOwn(en, text) ? text : Object.keys(en).find(key => en[key] === text);
      if (key) targets.push({node, original:node.textContent.replace(text, key)});
    }
    for (const node of root.querySelectorAll('[placeholder],[aria-label],[title]')) {
      for (const attribute of ['placeholder','aria-label','title']) {
        const original = node.getAttribute(attribute);
        const key = Object.hasOwn(en, original) ? original : Object.keys(en).find(key => en[key] === original);
        if (original && key) targets.push({node, attribute, original:key});
      }
    }
  }
  function apply() {
    for (const target of targets) {
      const original = target.original, trimmed = original.trim();
      const translated = original.replace(trimmed, t(trimmed));
      if (target.attribute) target.node.setAttribute(target.attribute, translated);
      else {
        // Dynamic fields may now contain a server URL or other user data.
        const current = target.node.textContent;
        if (current === original || current === original.replace(trimmed, en[trimmed])) target.node.textContent = translated;
      }
    }
    document.documentElement.lang = language;
    for (const selector of document.querySelectorAll('.language-select')) selector.value = language;
  }
  function setLanguage(value) {
    language = value === 'en' ? 'en' : 'it';
    try { localStorage.setItem('clone-coolify.language', language); } catch {}
    if (typeof document !== 'undefined') apply();
  }
  rebuildPatterns();
  return {t, capture, apply, setLanguage, get language(){return language;}, get locale(){return language === 'en' ? 'en-GB' : 'it-IT';}, en, rebuildPatterns};
})();
Object.assign(CloneI18n.en, {
  'Premi Applica ruoli per usare la nuova scelta. Le credenziali salvate vengono riutilizzate.':'Choose Apply roles to use this selection. Stored credentials will be reused.',
  'Scegli trasmittente e ricevente':'Choose source and destination',
  'Una riga per ogni server salvato. Scegli i ruoli senza reinserire le credenziali.':'One row per saved server. Choose roles without entering credentials again.',
  'Server salvato':'Saved server',
  'Salva almeno due server in Connessioni per scegliere i ruoli.':'Save at least two servers in Connections to choose roles.',
  'I tuoi server, salvati una volta.':'Your servers, saved once.',
  'Qui salvi e modifichi i server. La scelta di trasmittente e ricevente si trova in Panoramica.':'Save and edit servers here. Choose source and destination in Overview.',
  'Trasmittente: {name}':'Source: {name}', 'Ricevente: {name}':'Destination: {name}',

  'Server salvati e ruoli':'Saved servers and roles',
  'Salva più istanze Coolify e scegli quale trasmette e quale riceve per la prossima copia.':'Save multiple Coolify instances and choose the source and destination for the next copy.',
  'Trasmittente (sorgente)':'Transmitting server (source)', 'Ricevente (destinazione)':'Receiving server (destination)',
  'Il ricevente deve essere vuoto e avere un token con lettura, dati sensibili, scrittura e deploy. Cambiare ruolo non modifica i permessi del token.':'The destination must be empty and its token must allow read, sensitive data, write and deploy. Changing roles does not change token permissions.',
  'Inverti ruoli':'Swap roles', 'Applica ruoli':'Apply roles', 'Aggiungi o modifica un server':'Add or edit a server',
  'Server da modificare':'Server to edit', 'Nome riconoscibile':'Display name',
  'Le credenziali restano cifrate. Per modificare un server già salvato puoi lasciare vuoto il token per conservarlo.':'Credentials remain encrypted. When editing a saved server, leave the token empty to keep the stored one.',
  'Salva server':'Save server', 'Seleziona un server salvato':'Select a saved server', 'Nuovo server':'New server',
  'Ruoli invertiti nella selezione. Premi Applica ruoli per confermare.':'Role selections swapped. Choose Apply roles to confirm.',
  'Ruoli salvati. Ricarica l’elenco e ripeti l’analisi prima della copia.':'Roles saved. Reload resources and analyze again before copying.',
  'Server salvato. Puoi sceglierlo come trasmittente o ricevente.':'Server saved. You can select it as source or destination.',
  'Server salvato non trovato':'Saved server not found',
  'Configurazione server non valida: controllare campi e token API':'Invalid server configuration: check the fields and API token',
  'Limite di 100 server salvati raggiunto':'The limit of 100 saved servers has been reached',
  'Selezionare trasmittente e ricevente':'Select source and destination servers',
  'Selezionare due server salvati diversi':'Select two different saved servers',
  'Trasmittente e ricevente devono essere server diversi':'Source and destination must be different servers',

  'Riprendi ripristino':'Resume restoration',
  'Verrà usato il backup originale. La sorgente rimane in esecuzione. Il recupero verifica le risorse create dal job e si ferma se il database destinazione contiene dati.':'The original backup will be used. The source keeps running. Recovery checks the resources created by this job and stops if the destination database contains data.',
  'Accetto che le scritture successive al backup non siano incluse nella copia.':'I accept that writes made after the backup are not included in the copy.',
  'Scrivi RIPRENDI RIPRISTINO':'Type RIPRENDI RIPRISTINO', 'Ripristino avviato dal backup conservato.':'Restoration started from the retained backup.',
  'verifica_recupero':'Recovery checks', 'Versione PostgreSQL non verificabile':'Unable to verify PostgreSQL version',
  'Versione PostgreSQL sorgente non registrata: ripetere l’analisi':'Source PostgreSQL version not recorded: analyze again',
  'Versioni principali PostgreSQL diverse: ripristino bloccato':'PostgreSQL major versions differ: restoration blocked',
  'Risorse destinazione cambiate: recupero bloccato':'Destination resources changed: recovery blocked',
  'Identità destinazione cambiata: recupero bloccato':'Destination identity changed: recovery blocked',
  'La destinazione deve contenere solo le copie ferme di questo job':'The destination must contain only the stopped copies created by this job',
  'Configurazione database destinazione cambiata':'Destination database configuration changed',
  'Applicazione destinazione già avviata: recupero bloccato':'Destination application has already been started: recovery blocked',
  'Configurazione applicazione destinazione cambiata':'Destination application configuration changed',
  'Variabili destinazione cambiate: recupero bloccato':'Destination variables changed: recovery blocked',
  'Job non idoneo al recupero automatico':'Job not eligible for automatic recovery',
  'Verifica del recupero dal backup esistente; sorgente non fermata':'Checking recovery from the existing backup; source not stopped',
  'Identità server cambiata: recupero bloccato':'Server identity changed: recovery blocked',
  'Database sorgente cambiato: recupero bloccato':'Source database changed: recovery blocked',
  'Percorso backup non valido':'Invalid backup path',
  'Il database destinazione contiene dati: nessuna sovrascrittura consentita':'The destination database contains data: overwriting is not allowed',
  'Versione PostgreSQL compatibile e destinazione vuota verificate; ripristino del backup conservato':'Compatible PostgreSQL version and empty destination verified; restoring retained backup',
  'Ripristino completato dal backup originale; destinazione ferma per la verifica finale':'Restoration from original backup completed; destination stopped for final verification',
  'Recupero non riuscito; controllare configurazione e backup':'Recovery failed; check configuration and backup',
  'Confermare il ripristino dal backup originale':'Confirm restoration from the original backup',
  'Connessioni modificate: recupero bloccato':'Connections changed: recovery blocked',
  'Progetto destinazione cambiato: recupero bloccato':'Destination project changed: recovery blocked',
  "L'istanza gestisce più server: specificare l'UUID del server nella connessione":'The instance manages multiple servers: specify the server UUID in the connection',
  'La destinazione contiene già risorse Coolify: nessuna scrittura consentita':'The destination already contains Coolify resources: no writes allowed',
  'La destinazione contiene container estranei a Coolify':'The destination contains containers unrelated to Coolify',
  "Selezionare almeno un'applicazione o un database da clonare":'Select at least one application or database to clone',
  "Una risorsa selezionata non è più disponibile: ricaricare l'elenco":'A selected resource is no longer available: reload the list',
  'Identità dei server non verificabile':'Server identities could not be verified', 'Sorgente e destinazione coincidono':'Source and destination are the same',
  'Le versioni Coolify devono coincidere':'Coolify versions must match', 'Architetture CPU diverse':'CPU architectures differ',
  'La clonazione completa di istanze con più server gestiti richiede un adattatore dedicato':'Cloning instances with multiple managed servers requires a dedicated adapter',
  "Stack Services/Compose rilevati: l'adattatore di copia completa non è ancora disponibile":'Services/Compose stacks detected: the full-copy adapter is not yet available',
  'Container esterni o stack non riconosciuti sulla sorgente: impossibile fermare tutti gli scrittori in modo affidabile':'External containers or unrecognized stacks on the source: unable to reliably stop all writers',
  'Nessuna risorsa clonabile rilevata':'No clonable resources found',
  'Copia con fermo delle applicazioni sorgente; nessun cambio DNS automatico.':'Copying requires source application downtime; no automatic DNS changes.',
  "La destinazione rimane ferma dopo la copia: l'avvio può duplicare cron, email, webhook e pagamenti.":'The destination stays stopped after copying: starting it may duplicate cron jobs, emails, webhooks and payments.',
  "Creazione database, credenziali, ripristino dati e rimappatura dei collegamenti dell'app sono automatici durante la clonazione.":'Database creation, credentials, data restoration and application reference remapping are automatic during cloning.',
  'Utenti Coolify, impostazioni globali, cron, registry, backup pianificati e servizi esterni non sono clonati in questa release.':'Coolify users, global settings, cron jobs, registries, scheduled backups and external services are not cloned in this release.',
  'Serve spazio locale per backup cifrati e sulla destinazione per tutti i volumi.':'Local space is required for encrypted backups and destination space for all volumes.',
  'Saranno copiate e fermate solo le risorse selezionate. Le altre restano invariate: sospendere eventuali loro scritture verso i database selezionati.':'Only selected resources will be copied and stopped. Other resources remain unchanged: suspend any writes they make to selected databases.',
  'I domini originali saranno registrati sulla destinazione; DNS invariato.':'Original domains will be registered on the destination; DNS remains unchanged.',
  'UUID server non trovato o non visibile al token':'Server UUID not found or not visible to the token', 'Questa release richiede Docker Linux senza Swarm':'This release requires Docker on Linux without Swarm',
  'API e SSH devono puntare allo stesso host; proxy esterni non supportati in questa release':'API and SSH must point to the same host; external proxies are not supported in this release',
  "il server gestito da Coolify non coincide con l'host SSH":'the server managed by Coolify does not match the SSH host',
  'Progetto/ambiente non ricostruibile dal token':'Project/environment cannot be recreated from token access',
  'Richiesto esattamente un container esistente per risorsa':'Exactly one existing container is required per resource',
  'La risorsa sorgente deve essere avviata per il controllo prima della copia':'The source resource must be running for the pre-copy check',
  'Applicazione Compose: adattatore non disponibile':'Compose application: adapter unavailable', 'Immagine Docker assente o non visibile':'Docker image missing or not visible',
  'File mount: copia completa non ancora supportata':'File mounts: full copying not yet supported', 'Storage API e mount del container non corrispondono':'API storages and container mounts do not match',
  'Etichette proxy manuali: rimappatura dedicata necessaria':'Manual proxy labels: dedicated remapping required',
  'GPU/autenticazione proxy richiedono un adattatore dedicato':'GPU/proxy authentication requires a dedicated adapter',
  'Motore database non ancora supportato (PostgreSQL, MySQL, MariaDB disponibili)':'Database engine not yet supported (PostgreSQL, MySQL and MariaDB available)',
  'Database con mount aggiuntivi: necessaria verifica dedicata':'Database with additional mounts: dedicated verification required',
  'Database pubblico: dipendenze e client esterni da rimappare':'Public database: dependencies and external clients need remapping',
  'Variabili database aggiuntive: copia completa da adattare':'Additional database variables: full-copy adapter required',
  'Variabili bloccate, condivise o non leggibili':'Locked, shared or unreadable variables', 'Bind mount o tmpfs: impossibile garantire copia completa':'Bind mounts or tmpfs: full copy cannot be guaranteed',
  'Volume condiviso con un container non selezionato: includere tutti gli scrittori o separare i dati':'Volume shared with an unselected container: include all writers or separate the data',
  'Credenziali o database non leggibili: richiedere token read:sensitive':'Credentials or database unreadable: a read:sensitive token is required',
  'Sorgente Git/build pack: adattatore non disponibile':'Git source/build pack: adapter unavailable', 'Dockerfile senza repository: adattatore non disponibile':'Dockerfile without repository: adapter unavailable',
  'Variabili con riferimenti non risolti o valori mascherati':'Variables with unresolved references or masked values', 'Volume non descritto dagli storage API':'Volume not described by API storages',
  'Configurazione avanzata da adattare: {field}':'Advanced configuration requires an adapter: {field}',
  'saranno importate le credenziali GitHub necessarie; auto deploy e anteprime disattivati sulla copia. Il codice sarà ricostruito da Git al successivo deploy manuale.':'required GitHub credentials will be imported; auto deploy and previews are disabled on the copy. Code will be rebuilt from Git on the next manual deployment.',
  'Variabile con indirizzo esplicito della sorgente: rimappatura manuale richiesta':'Variable contains an explicit source address: manual remapping required',
  'Nome volume effettivo diverso dal nome API: rimappatura non verificabile in questa release':'Actual volume name differs from API name: remapping cannot be verified in this release',
  'Dipendenza esclusa dalla selezione: {name} ({uuid})':'Dependency excluded from selection: {name} ({uuid})',
  'API HTTP non cifrata: usare HTTPS o abilitare esplicitamente HTTP sulla rete fidata':'Unencrypted HTTP API: use HTTPS or explicitly allow HTTP on a trusted network',
  'ATTENZIONE: riavvio sorgente non riuscito. Usare Recupera sorgente o intervenire via SSH.':'WARNING: source restart failed. Use Recover source or intervene via SSH.',
  'Accesso richiesto':'Sign-in required', "Applicazioni sorgente riavviate; il clone rappresenta l'istante del backup":'Source applications restarted; the clone represents the backup snapshot',
  'Arresto destinazione da verificare manualmente':'Destination shutdown must be checked manually', "Attendere la conclusione dell'operazione corrente":'Wait for the current operation to finish',
  'Backup cifrato verificato: {uuid}':'Encrypted backup verified: {uuid}', 'Backup incompleto: marcatore finale assente':'Incomplete backup: final marker missing',
  'Backup remoto fallito; il file parziale non verrà ripristinato':'Remote backup failed; the partial file will not be restored',
  'Backup troncato':'Truncated backup', 'Backup vuoto':'Empty backup', 'Blocco backup non valido':'Invalid backup block',
  'Checksum del backup non corrispondente':'Backup checksum mismatch', 'Chiave GitHub non leggibile: necessario read:sensitive':'GitHub key unreadable: read:sensitive required',
  'Chiave SSH o known_hosts assente nella cartella ssh':'SSH key or known_hosts missing from the ssh directory', 'Chiave master Fernet non valida':'Invalid Fernet master key',
  'Cluster PostgreSQL con più database: copia completa non supportata da questo adattatore':'PostgreSQL cluster with multiple databases: full copy not supported by this adapter',
  'Comando SSH fallito: verificare host key, accesso e privilegi (output remoto omesso)':'SSH command failed: check host key, access and privileges (remote output omitted)',
  'Confermare fermo sorgente, assenza di scrittori esterni e destinazione vuota':'Confirm source downtime, absence of external writers and an empty destination',
  'Configurare prima le connessioni':'Configure connections first', 'Configurare prima le due connessioni':'Configure both connections first',
  'Configurazione sorgente cambiata dopo il piano':'Source configuration changed after analysis', 'Connessione API fallita (rete, TLS o timeout)':'API connection failed (network, TLS or timeout)',
  'Connessioni modificate: rigenerare il piano':'Connections changed: regenerate the plan', 'Connessioni originali non disponibili':'Original connections unavailable',
  'Container destinazione non sano':'Destination container is unhealthy', 'Container sorgente cambiato o fermo dopo il piano':'Source container changed or stopped after analysis',
  'Controlli aggiornati di identità, destinazione vuota e risorse sorgente':'Rechecking identity, empty destination and source resources',
  'Coolify: HTTP {code} su {method} {path}':'Coolify: HTTP {code} on {method} {path}',
  'Copia completata; destinazione ferma. Verificare mount, applicazioni e DNS prima del passaggio del traffico.':'Copy completed; destination stopped. Check mounts, applications and DNS before switching traffic.',
  'Creata risorsa {group}: {old} → {new}':'Created resource {group}: {old} → {new}',
  'Credenziali GitHub cambiate dopo il piano':'GitHub credentials changed after analysis', 'Credenziali GitHub incomplete o mascherate':'GitHub credentials incomplete or masked',
  'Dati inattesi dopo la fine del backup':'Unexpected data after the end of the backup', 'Dati non validi':'Invalid data',
  'Errore interno; verificare configurazione e compatibilità (dettagli sensibili omessi)':'Internal error; check configuration and compatibility (sensitive details omitted)',
  'Formato backup non valido':'Invalid backup format', 'Formato elenco inatteso: {path}':'Unexpected list format: {path}',
  'Gli URL delle due istanze devono essere diversi':'The two instance URLs must differ', 'Identificatore remoto non valido':'Invalid remote identifier',
  'Identità SSH cambiata dopo il piano':'SSH identity changed after analysis', 'Identità sorgente cambiata: recupero automatico bloccato':'Source identity changed: automatic recovery blocked',
  'Il database postgres contiene dati aggiuntivi: non verranno ignorati':'The postgres database contains additional data: it will not be ignored',
  'Integrazione GitHub sorgente non leggibile':'Source GitHub integration unreadable', 'Integrità o chiave del backup non valida':'Invalid backup integrity or key',
  'Inventario cambiato dopo il piano':'Inventory changed after analysis', 'Istanza MySQL/MariaDB con più database: adattatore dedicato richiesto':'MySQL/MariaDB instance with multiple databases: dedicated adapter required',
  "L'immagine database è cambiata (tag mobile): fissare la stessa immagine prima della copia":'The database image changed (moving tag): pin the same image before copying',
  'Nome volume Docker non valido':'Invalid Docker volume name', 'Operazione non trovata':'Operation not found', 'Origine della richiesta non autorizzata':'Unauthorized request origin',
  'Password non valida':'Invalid password', 'Piano assente, bloccato o scaduto; analizzare di nuovo':'Plan missing, blocked or expired; analyze again',
  "Piano bloccato, modificato o scaduto: ripetere l'analisi":'Plan blocked, changed or expired: analyze again',
  'Recupero sorgente richiesto dall’operatore: comando di avvio completato':'Source recovery requested by operator: start command completed',
  "Recupero sorgente richiesto dall'operatore: comando di avvio completato":'Source recovery requested by operator: start command completed',
  'Richiesta troppo grande':'Request too large', "Ripristinato l'avvio delle applicazioni sorgente":'Source applications restarted',
  'Ripristino SSH interrotto':'SSH restoration interrupted', 'Ripristino completato: {uuid}':'Restoration completed: {uuid}',
  'Ripristino remoto fallito; destinazione mantenuta ferma':'Remote restoration failed; destination kept stopped', 'Risposta Coolify non JSON':'Non-JSON Coolify response',
  'Ruoli PostgreSQL aggiuntivi: adattatore dedicato richiesto':'Additional PostgreSQL roles: dedicated adapter required',
  'SSH non disponibile o comando scaduto':'SSH unavailable or command timed out', "Selezionare almeno una risorsa da clonare prima dell'analisi":'Select at least one resource to clone before analysis',
  'Sospensione delle applicazioni sorgente; database disponibili per il dump':'Stopping source applications; databases available for dumping',
  'Tabelle non InnoDB: backup transazionale non sufficiente':'Non-InnoDB tables: transactional backup is insufficient', 'Timeout di avvio della risorsa destinazione':'Destination resource startup timed out',
  'Token CSRF non valido':'Invalid CSRF token', 'Troppi tentativi: riprovare fra cinque minuti':'Too many attempts: try again in five minutes',
  'Un volume selezionato è ora condiviso con un container escluso: rigenerare il piano':'A selected volume is now shared with an excluded container: regenerate the plan',
  "Un'operazione è già in corso":'An operation is already running', 'Una applicazione sorgente è ripartita durante il fermo':'A source application restarted during downtime',
  'Utenti MySQL/MariaDB aggiuntivi: adattatore dedicato richiesto':'Additional MySQL/MariaDB users: dedicated adapter required',
  'Variabili sorgente cambiate dopo il piano':'Source variables changed after analysis', 'Volume destinazione già esistente: nessuna sovrascrittura consentita':'Destination volume already exists: overwriting is not allowed'
});
CloneI18n.rebuildPatterns();
if (typeof module !== 'undefined') module.exports = CloneI18n;
