const test = require('node:test');
const assert = require('node:assert/strict');
const ResourceSelection = require('../app/static/selection.js');
const resources = [
  {uuid:'app-a',group:'applications',database_uuids:['db-shared','db-private']},
  {uuid:'app-b',group:'applications',database_uuids:['db-shared']},
  {uuid:'stack',group:'services',embedded_databases:[{uuid:'mysql'}]},
  {uuid:'db-shared',group:'databases'},
  {uuid:'db-private',group:'databases'},
  {uuid:'db-orphan',group:'databases'},
];
test('selecting an application automatically selects all linked databases',()=>{
  const s=new ResourceSelection(resources);s.toggle('app-a',true);
  assert.deepEqual([...s.ids()].sort(),['app-a','db-private','db-shared']);
});
test('deselecting the last parent removes automatically selected databases',()=>{
  const s=new ResourceSelection(resources);s.toggle('app-a',true);s.toggle('app-a',false);
  assert.equal(s.ids().size,0);
});
test('shared database remains until the last selected parent is deselected',()=>{
  const s=new ResourceSelection(resources);s.toggle('app-a',true);s.toggle('app-b',true);s.toggle('app-a',false);
  assert.deepEqual([...s.ids()].sort(),['app-b','db-shared']);
  s.toggle('app-b',false);assert.equal(s.ids().size,0);
});
test('database required by an application cannot be silently deselected',()=>{
  const s=new ResourceSelection(resources);s.toggle('app-b',true);s.toggle('db-shared',false);
  assert(s.ids().has('db-shared'));
});
test('explicit database selection survives parent deselection',()=>{
  const s=new ResourceSelection(resources);s.toggle('db-shared',true);s.toggle('app-b',true);s.toggle('app-b',false);
  assert.deepEqual([...s.ids()],['db-shared']);
});
test('stack internal databases are selected through the stack, not as separate resources',()=>{
  const s=new ResourceSelection(resources);s.toggle('stack',true);
  assert.deepEqual([...s.ids()],['stack']);
});
test('restored plans do not accidentally turn implied databases into manual choices',()=>{
  const s=new ResourceSelection(resources,['app-b','db-shared']);s.toggle('app-b',false);
  assert.equal(s.ids().size,0);
});
test('select all includes unassociated databases and clear removes everything',()=>{
  const s=new ResourceSelection(resources);s.selectAll();assert.equal(s.ids().size,6);
  s.clear();assert.equal(s.ids().size,0);
});
