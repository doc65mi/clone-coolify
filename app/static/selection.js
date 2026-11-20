(function (root) {
  'use strict';
  class ResourceSelection {
    constructor(resources = [], selected = []) {
      this.resources = new Map(resources.map(resource => [resource.uuid, resource]));
      this.roots = new Set(selected.filter(id => this.resources.get(id)?.group !== 'databases' && this.resources.has(id)));
      const required = this.requiredDatabaseIds();
      this.manualDatabases = new Set(selected.filter(id => this.resources.get(id)?.group === 'databases' && !required.has(id)));
    }
    requiredDatabaseIds() {
      const result = new Set();
      for (const id of this.roots) for (const db of this.resources.get(id)?.database_uuids || []) {
        if (this.resources.get(db)?.group === 'databases') result.add(db);
      }
      return result;
    }
    requiredBy(id) {
      return [...this.roots].filter(app => (this.resources.get(app)?.database_uuids || []).includes(id));
    }
    ids() { return new Set([...this.roots, ...this.manualDatabases, ...this.requiredDatabaseIds()]); }
    toggle(id, checked) {
      const resource = this.resources.get(id);
      if (!resource) return;
      if (resource.group === 'databases') {
        if (!checked && this.requiredBy(id).length) return;
        if (checked) this.manualDatabases.add(id); else this.manualDatabases.delete(id);
      } else if (checked) this.roots.add(id); else this.roots.delete(id);
    }
    clear() { this.roots.clear(); this.manualDatabases.clear(); }
    selectAll() {
      for (const resource of this.resources.values()) if (resource.group !== 'databases') this.roots.add(resource.uuid);
      const required = this.requiredDatabaseIds();
      for (const resource of this.resources.values()) if (resource.group === 'databases' && !required.has(resource.uuid)) this.manualDatabases.add(resource.uuid);
    }
  }
  root.CloneSelection = ResourceSelection;
  if (typeof module !== 'undefined' && module.exports) module.exports = ResourceSelection;
})(typeof globalThis !== 'undefined' ? globalThis : this);
