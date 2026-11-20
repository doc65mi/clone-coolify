import json

from app.catalog import expand_database_selection, linked_source_catalog
from app.coolify import CloneError


def inventory():
    return {"project_details": [{"uuid":"project", "name":"Project", "environments":[{"id":1,"name":"production"}]}],
            "applications":[{"uuid":"app-one", "name":"App One", "environment_id":1},
                            {"uuid":"app-two", "name":"App Two", "environment_id":1}],
            "databases":[{"uuid":"db-one", "name":"primary-db", "environment_id":1},
                         {"uuid":"db-two", "name":"secondary-db", "environment_id":1}],
            "services":[]}


class CatalogAPI:
    def __init__(self, variables=None, details=None, fail=None):
        self.variables=variables or {}
        self.details=details or {}
        self.fail=fail or set()
        self.calls=[]

    def listing(self,path):
        self.calls.append(path)
        if path in self.fail:
            raise CloneError("sensitive error must not escape")
        return self.variables.get(path,[])

    def call(self,method,path):
        self.calls.append(path)
        if path in self.fail:
            raise CloneError("sensitive error must not escape")
        return self.details.get(path,{})


def test_database_reference_groups_without_exposing_credentials():
    api=CatalogAPI({"applications/app-one/envs":[{"key":"DATABASE_URL","value":"postgres://user:PRIVATE-PASSWORD@db-one:5432/main"}]})
    rows=linked_source_catalog(inventory(),api)
    one=next(r for r in rows if r["uuid"]=="app-one")
    db=next(r for r in rows if r["uuid"]=="db-one")
    assert one["database_uuids"]==["db-one"]
    assert db["application_uuids"]==["app-one"]
    assert "PRIVATE-PASSWORD" not in json.dumps(rows)
    assert "DATABASE_URL" not in json.dumps(rows)


def test_same_project_is_not_enough_to_infer_a_database():
    rows=linked_source_catalog(inventory(),CatalogAPI())
    assert all(not r["database_uuids"] for r in rows)


def test_shared_database_has_both_parents():
    variables={f"applications/{app}/envs":[{"key":"DATABASE_URL","value":"postgres://u:p@db-one/main"}]
               for app in ("app-one","app-two")}
    rows=linked_source_catalog(inventory(),CatalogAPI(variables))
    db=next(r for r in rows if r["uuid"]=="db-one")
    assert db["application_uuids"]==["app-one","app-two"]


def test_database_name_is_matched_as_host_not_as_username():
    api=CatalogAPI({"applications/app-one/envs":[{"key":"DATABASE_URL","value":"postgres://primary-db:password@external.example/main"}],
                    "applications/app-two/envs":[{"key":"DB_HOST","value":"primary-db"}]})
    rows=linked_source_catalog(inventory(),api)
    assert rows[0]["database_uuids"]==[]
    assert rows[1]["database_uuids"]==["db-one"]


def test_resolved_shared_variable_can_identify_database_without_returning_value():
    api=CatalogAPI({"applications/app-one/envs":[{"key":"DATABASE_URL","value":"{{project.DB_URL}}","real_value":"postgres://user:SECRET@db-two/main"}]})
    rows=linked_source_catalog(inventory(),api)
    assert rows[0]["database_uuids"]==["db-two"]
    assert "SECRET" not in json.dumps(rows)


def test_inaccessible_or_locked_variables_are_reported_without_guessing():
    api=CatalogAPI({"applications/app-one/envs":[{"key":"DATABASE_URL","value":"postgres://u:p@db-one/main","is_shown_once":True}]},
                   fail={"applications/app-two/envs"})
    rows=linked_source_catalog(inventory(),api)
    assert rows[0]["database_uuids"]==[] and rows[0]["dependency_warning"]
    assert rows[1]["database_uuids"]==[] and rows[1]["dependency_warning"]
    assert "sensitive error" not in json.dumps(rows)


def test_uuid_prefix_is_not_an_actual_reference():
    api=CatalogAPI({"applications/app-one/envs":[{"key":"DATABASE_URL","value":"postgres://u:p@db-one-other/main"}]})
    assert linked_source_catalog(inventory(),api)[0]["database_uuids"]==[]


def test_internal_stack_database_is_nested_but_not_selected_as_standalone_resource():
    inv=inventory()
    inv["services"]=[{"uuid":"wordpress","name":"WordPress","environment_id":1}]
    api=CatalogAPI(details={"services/wordpress":{"databases":[
        {"uuid":"internal-mysql","name":"mysql","image":"mysql:8","password":"PRIVATE"},
        {"uuid":"removed-db","name":"old","is_removed_from_compose":True}]}})
    rows=linked_source_catalog(inv,api)
    stack=next(r for r in rows if r["uuid"]=="wordpress")
    assert stack["embedded_databases"]==[{"uuid":"internal-mysql","name":"mysql","kind":"mysql"}]
    assert expand_database_selection({"wordpress"},rows)==["wordpress"]
    assert "PRIVATE" not in json.dumps(rows)


def test_plan_expansion_adds_only_selected_application_dependencies():
    api=CatalogAPI({"applications/app-one/envs":[{"key":"DB_HOST","value":"db-one"}],
                   "applications/app-two/envs":[{"key":"DB_HOST","value":"db-two"}]})
    rows=linked_source_catalog(inventory(),api,{"app-one"})
    assert "applications/app-two/envs" not in api.calls
    assert expand_database_selection({"app-one"},rows)==["app-one","db-one"]
