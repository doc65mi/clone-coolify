const test = require('node:test');
const assert = require('node:assert/strict');
const i18n = require('../app/static/i18n.js');

test('language switches both ways and formats placeholders without translating resource names', () => {
  i18n.setLanguage('en');
  assert.equal(i18n.t('Connessioni'), 'Connections');
  assert.equal(i18n.t('Clona {name}', {name:'Produzione italiana'}), 'Clone Produzione italiana');
  assert.equal(i18n.locale, 'en-GB');
  i18n.setLanguage('it');
  assert.equal(i18n.t('Connessioni'), 'Connessioni');
  assert.equal(i18n.t('Clona {name}', {name:'Production'}), 'Clona Production');
  assert.equal(i18n.locale, 'it-IT');
});

test('parameterized warnings and resource prefixes preserve identifiers', () => {
  i18n.setLanguage('en');
  assert.equal(i18n.t('db-produzione: Configurazione avanzata da adattare: custom_labels'),
    'db-produzione: Advanced configuration requires an adapter: custom_labels');
  assert.equal(i18n.t('Analisi completata: 3 controlli da risolvere.'), 'Analysis complete: 3 checks need attention.');
  assert.equal(i18n.t('Dipendenza esclusa dalla selezione: Nome con spazi (db-123)'),
    'Dependency excluded from selection: Nome con spazi (db-123)');
  assert.equal(i18n.t('https://server.example:8000'), 'https://server.example:8000');
});

test('security messages translate while the execution confirmation stays literal', () => {
  i18n.setLanguage('en');
  assert.equal(i18n.t('Password non valida'), 'Invalid password');
  assert.equal(i18n.t('Configurazione sorgente cambiata dopo il piano'), 'Source configuration changed after analysis');
  assert.equal(i18n.t('Scrivi CLONA DESTINAZIONE VUOTA'), 'Type CLONA DESTINAZIONE VUOTA');
  assert.equal(i18n.t('CLONA DESTINAZIONE VUOTA'), 'CLONA DESTINAZIONE VUOTA');
});

test('invalid preferences fall back to Italian', () => {
  i18n.setLanguage('unsupported');
  assert.equal(i18n.language, 'it');
});

test('language preference survives module reloads', () => {
  let saved;
  global.localStorage = {getItem:()=>saved, setItem:(key,value)=>{saved=value;}};
  i18n.setLanguage('en');
  delete require.cache[require.resolve('../app/static/i18n.js')];
  const reloaded = require('../app/static/i18n.js');
  assert.equal(reloaded.language, 'en');
  delete global.localStorage;
});
