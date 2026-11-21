Clone Coolify
=============

**Select your applications. Copy their configuration and data. Stay in control.**

Italiano e English · Version 0.8.0 · Experimental / Sperimentale

Italiano
--------

Server salvati e scelta dei ruoli
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Salva più installazioni Coolify con nomi riconoscibili. In Connessioni
scegli il Trasmittente e il Ricevente, anche invertendoli, e conferma
con Applica ruoli. Le credenziali rimangono cifrate; modificando un
profilo puoi lasciare vuoto il token per conservare quello salvato.

Il ricevente deve essere vuoto e avere un token con scrittura e deploy,
oltre a lettura e dati sensibili. Il cambio ruolo non amplia i permessi.
Ogni profilo conserva la propria chiave SSH. Una sola coppia alla volta:
il cambio invalida elenco e piano ed è bloccato durante le copie.

Scopo del progetto
~~~~~~~~~~~~~~~~~~

Clone Coolify è un'applicazione self-hosted pensata per copiare applicazioni
e database tra due installazioni Coolify indipendenti. Una dashboard permette
di consultare il server sorgente, scegliere cosa trasferire e analizzare
la selezione prima di avviare la clonazione.

L'obiettivo è ridurre il lavoro manuale necessario per ricreare le risorse
su un altro server, mantenendo il controllo su quali applicazioni copiare
e quando farlo. Il programma usa le API Coolify per la configurazione
e SSH per il backup e il ripristino dei dati.

Come funziona
~~~~~~~~~~~~~

1. Collega le due istanze tramite URL, token API e chiavi SSH dedicate.
2. Carica l'elenco delle applicazioni sorgenti. I database riconosciuti come
   collegati sono mostrati sotto l'applicazione e selezionati insieme ad essa.
3. Analizza la selezione: questa fase effettua soltanto letture e segnala
   incompatibilità o dipendenze da risolvere.
4. Avvia la copia con una conferma esplicita. La creazione dei progetti,
   delle applicazioni e dei database supportati, il ripristino dei dati
   e la rimappatura dei collegamenti fanno parte della clonazione.

I nuovi identificativi possono essere diversi da quelli della sorgente:
il programma aggiorna i riferimenti UUID nelle variabili copiate.
Non ci sono clonazioni automatiche o pianificate.

Recupero del ripristino PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Gli aggiornamenti minori PostgreSQL della stessa versione principale sono
accettati dopo verifica SQL, anche se le immagini Docker differiscono.
Per blocchi immagine o avvio precedenti al ripristino, Operazioni può offrire Riprendi ripristino:
riusa il backup conservato soltanto se le applicazioni del job non sono
mai state avviate e il database è vuoto, con conferma esplicita. La sorgente non viene fermata
e le scritture successive al backup non sono incluse. Il recupero è limitato
a un database PostgreSQL e applicazioni senza volumi.

Lingua dell’interfaccia
~~~~~~~~~~~~~~~~~~~~~~

Scegli Italiano o English nel login o nella barra superiore. La preferenza
resta salvata nel browser e il cambio lingua conserva moduli e selezioni.
Interfaccia, guida, avvisi e registro eventi sono disponibili in entrambe
le lingue; nomi e dati delle risorse restano invariati.

Funzionalità disponibili
~~~~~~~~~~~~~~~~~~~~~~~

* Applicazioni Docker Image con configurazioni compatibili.
* Applicazioni collegate tramite GitHub App e build Dockerfile, con importazione
  delle credenziali necessarie e ricreazione della configurazione Git.
* PostgreSQL, MySQL e MariaDB nelle configurazioni supportate.
* Backup cifrati e copia dei volumi nominati verificabili.
* Analisi preventiva, registro delle operazioni e recupero della sorgente
  in caso di errori gestiti.

Limiti da conoscere
~~~~~~~~~~~~~~~~~~

Questa versione è sperimentale: non è un clone universale di un'intera istanza.
Richiede una destinazione vuota, versioni Coolify uguali, un server gestito
per istanza e la stessa architettura CPU. Services/Compose, bind/file mount,
altri provider o build pack Git, database multipli o con ruoli aggiuntivi
e altre configurazioni non supportate bloccano il piano.

Durante il backup vengono sospese le applicazioni sorgenti selezionate,
poi riavviate. Dopo la copia la destinazione resta ferma: verifica funzionale,
attivazione e cambio DNS rimangono sotto il controllo dell'operatore.
Non viene eseguita una sincronizzazione continua delle nuove scritture.

Per le applicazioni Git, il codice viene ricostruito al successivo deploy
manuale; un riferimento ``HEAD`` può recuperare codice più recente rispetto
al container sorgente. Auto deploy e anteprime sono disattivati sulla copia.
Utenti e impostazioni globali Coolify, cron, registry e servizi esterni
non vengono clonati.

Per iniziare
~~~~~~~~~~~~

Servono Python 3.11+, un client OpenSSH e accessi API/SSH ai due server.
Sono disponibili un launcher Windows e una configurazione Docker Compose.

Consulta le `istruzioni di installazione e sicurezza <files%20MD/README.md>`_.
Il repository contiene solo codice, test e documentazione generica:
token, password, chiavi SSH, configurazioni dei server, dati e backup
devono rimanere locali.

English
-------

Saved servers and role selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Save multiple Coolify installations with recognizable names. In Connections,
choose the source and destination, swap them if needed, and confirm with
Apply roles. Credentials stay encrypted. When editing an existing profile,
leave the token empty to keep the stored one.

The destination must be empty and its token needs write and deploy access
in addition to read and sensitive data. Changing roles does not expand
permissions. Each profile keeps its own SSH key. Only one pair is active
at a time: changes invalidate the selection and plan and are blocked
during a copy.

Project purpose
~~~~~~~~~~~~~~~

Clone Coolify is a self-hosted application for copying applications and
databases between two independent Coolify installations. Its dashboard lets
you browse the source server, choose what to transfer and analyze your
selection before starting a clone.

The goal is to reduce the manual work involved in recreating resources on
another server while keeping you in control of what gets copied and when.
The application uses the Coolify API for configuration and SSH for data
backup and restoration.

How it works
~~~~~~~~~~~~

1. Connect both instances using their URLs, API tokens and dedicated SSH keys.
2. Load the source application list. Recognized linked databases appear below
   their application and are selected automatically with it.
3. Analyze the selection. This step only reads information and reports
   incompatible configurations or dependencies that need attention.
4. Start the copy with explicit confirmation. Creating supported projects,
   applications and databases, restoring data and remapping references
   are part of the cloning process.

Destination identifiers may differ from the original ones: the application
updates UUID references in copied environment variables.
There are no automatic or scheduled clones.

PostgreSQL restoration recovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Minor PostgreSQL updates within the same major version are accepted after
SQL verification, even when Docker image hashes differ. For image-check or startup failures before restoration,
Operations may offer Resume restoration: it reuses
the retained backup only if the job’s destination applications have never
been started and the database is empty, with explicit confirmation. The source stays running, and later
writes are not included. Recovery is limited to one PostgreSQL database
and applications without volumes.

Interface language
~~~~~~~~~~~~~~~~~~

Choose Italiano or English on the sign-in screen or in the top bar.
The browser remembers your preference, and switching language preserves
forms and selections. The interface, guide, warnings and event logs are
available in both languages; resource names and data remain unchanged.

Available features
~~~~~~~~~~~~~~~~~~

* Docker Image applications with compatible configurations.
* GitHub App applications using Dockerfile builds, including required
  credential import and Git configuration recreation.
* PostgreSQL, MySQL and MariaDB in supported configurations.
* Encrypted backups and copying of verifiable named volumes.
* Preflight analysis, operation logs and source recovery after handled errors.

Current limitations
~~~~~~~~~~~~~~~~~~~

This is an experimental release, not a universal full-instance clone.
It requires an empty destination, matching Coolify versions, one managed
server per instance and the same CPU architecture. Services/Compose,
bind/file mounts, other Git providers or build packs, multiple databases
or additional database roles, and other unsupported configurations
block the plan.

Selected source applications are stopped during backup acquisition and then
restarted. The destination stays stopped after copying: functional validation,
activation and DNS changes remain under the operator's control.
Subsequent source writes are not continuously synchronized.

Git applications are rebuilt on their next manual deployment. A ``HEAD``
reference may fetch newer code than the original running container.
Auto deploy and preview deployments are disabled on the copy.
Coolify users and global settings, cron jobs, registries and external
services are not cloned.

Getting started
~~~~~~~~~~~~~~~

You need Python 3.11+, an OpenSSH client and API/SSH access to both servers.
A Windows launcher and Docker Compose configuration are included.

See the `installation and security guide (Italian) <files%20MD/README.md>`_.
This repository contains only code, tests and generic documentation.
Tokens, passwords, SSH keys, server configurations, data and backups
must remain local.

Validation / Verifiche
---------------------

92 Python tests and 13 JavaScript tests passed for the application code;
read-only API/SSH analysis was checked on Coolify 4.7.6. A full production
migration has not been run to validate this release. Test a complete clone
on disposable instances before operational use.

92 test Python e 13 JavaScript superati per il codice applicativo;
analisi API/SSH in sola lettura verificata su Coolify 4.7.6.
La release non è stata collaudata con una migrazione completa in produzione:
provare prima una clonazione su istanze usa-e-getta.
