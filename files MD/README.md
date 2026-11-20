# Clone Coolify

Applicazione self-hosted per analizzare e copiare applicazioni e database tra due installazioni Coolify indipendenti. Backend Python/FastAPI, interfaccia web in italiano e inglese e backup cifrati. Versione **0.6.0**, sperimentale.

## Lingua dell’app

Scegli Italiano o English nel login o nella barra superiore. La preferenza viene conservata nel browser; il cambio lingua mantiene moduli e selezioni. Sono tradotti interfaccia, guida, piano, avvisi e registro eventi. Nomi, valori di configurazione e frase di conferma restano invariati.

## Funzionamento

1. Configura URL, token API e chiavi SSH dei due server nella dashboard.
2. Carica l'elenco della sorgente e scegli le applicazioni. I database riconosciuti dalle variabili vengono mostrati sotto l'app e inclusi automaticamente.
3. Analizza la selezione: l'analisi effettua solo letture e segnala i limiti prima di qualsiasi copia.
4. Avvia manualmente la clonazione con conferma esplicita. Creazione di progetti, applicazioni, database, credenziali DB, ripristino e rimappatura degli UUID sono compresi.

Non ci sono avvii automatici o pianificati. Il backup richiede una sospensione delle applicazioni selezionate sulla sorgente; vengono riavviate dopo l'acquisizione. La destinazione resta ferma dopo la copia. Attivazione, verifica funzionale e cambio DNS sono responsabilità dell'operatore.

## Installazione locale

Richiede Python 3.11 o successivo e client OpenSSH. Sui server servono Docker Linux, Python 3 e tar, accesso SSH amministrativo e API Coolify abilitate.

```sh
python -m pip install -r requirements.txt
python tools/setup.py
python tools/run.py
```

Su Windows è disponibile `Avvia-Clone-Coolify.cmd`. Apri `http://127.0.0.1:8787/` e usa `CLONE_ADMIN_PASSWORD` generata in `.env`. Non pubblicare `.env` e non perdere `CLONE_MASTER_KEY`, necessaria per decifrare i dati.

Per Docker, dopo aver creato `.env` e configurato `ssh/`, usa `docker compose up --build -d`. La porta è associata solo a localhost. L'immagine Docker va collaudata nel proprio ambiente; non è stata verificata end-to-end durante lo sviluppo.

## Connessioni

Usa due istanze della stessa versione Coolify, un solo server gestito per istanza, stessa architettura CPU e destinazione vuota. La destinazione viene controllata tramite API e inventario Docker. Non vengono sovrascritte risorse esistenti.

Token sorgente: `read` e `read:sensitive`. Token destinazione: anche `write` e `deploy`. Per leggere i segreti è necessario un account Coolify Owner/Admin. Non serve `delete`.

Configura chiavi dedicate in `ssh/` e registra in `ssh/known_hosts` le host key verificate tramite un canale attendibile. Non disabilitare `StrictHostKeyChecking`. HTTPS è consigliato; HTTP richiede consenso esplicito nella configurazione.

## Supporto e limiti

- Applicazioni Docker Image con configurazioni compatibili e volumi nominati verificabili.
- Applicazioni GitHub App con build Dockerfile: importazione delle credenziali necessarie, ricreazione della configurazione Git e impostazioni di build. Auto deploy e anteprime vengono disattivati sulla copia. Il codice viene ricostruito al successivo deploy manuale; un riferimento `HEAD` può quindi recuperare codice più recente del container originario.
- PostgreSQL, MySQL e MariaDB con un database applicativo e utenti supportati. Dump nativi cifrati, ripristino e controllo dell'immagine database.
- Le label gestite da Coolify vengono rigenerate; quelle modificate manualmente rimangono bloccate.

Services/Compose, altri provider/build pack Git, bind/file mount, database multipli o con ruoli aggiuntivi, variabili condivise/bloccate e altre configurazioni non supportate bloccano il piano. Utenti e impostazioni globali Coolify, cron, registry, DNS e servizi esterni non sono copiati. Non è un clone universale e non effettua una sincronizzazione continua.

Verifica della release: 64 test Python e 13 JavaScript superati; analisi API/SSH in sola lettura su Coolify 4.7.6. I test automatici verificano logica, sicurezza e percorsi simulati. Una clonazione completa va prima provata su istanze usa-e-getta: non è stata avviata alcuna migrazione di produzione per collaudare questa release.

## Sicurezza dei dati

Token, snapshot e credenziali sono cifrati con Fernet; i backup usano AES-GCM autenticato. Le chiavi SSH sono file locali e vanno protette con permessi adeguati. Sessioni locali, CSRF e limitazione dei tentativi proteggono la dashboard. Esporla in rete richiede un reverse proxy HTTPS e controlli di accesso.

Questo repository contiene solo codice, test e documentazione generica. `.env`, dati, configurazioni, log, backup, chiavi e note operative locali sono esclusi da Git.

## Test

```sh
python -m pytest -q
node --test tests/selection-model.test.cjs tests/i18n.test.cjs
node --check app/static/app.js
```
