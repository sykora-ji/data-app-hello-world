import streamlit as st
import toml
import os
import sys
import json
import importlib.metadata
import pandas as pd


def display_toml_content(title: str, file_path: str) -> None:
    """Render TOML file content in Streamlit."""
    st.title(title)
    try:
        content = toml.load(file_path)
        st.write(content)
    except FileNotFoundError:
        st.error(f'Soubor {file_path} nebyl nalezen.')
    except toml.TomlDecodeError:
        st.error(f'Soubor {file_path} má neplatný formát.')


def _mask(value: str) -> str:
    """Mask a sensitive value, keeping only the last 4 characters."""
    if not value:
        return value
    if len(value) <= 4:
        return '*' * len(value)
    return '…' + value[-4:]


def _resolve_workspace_id() -> tuple[str | None, str]:
    """Resolve the workspace id from env or the workspace manifest file.

    Returns a tuple of (workspace_id, source_description).
    """
    workspace_id = os.environ.get('WORKSPACE_ID')
    if workspace_id:
        return workspace_id, 'WORKSPACE_ID (env)'

    manifest_path = os.environ.get('KBC_WORKSPACE_MANIFEST_PATH')
    if not manifest_path:
        return None, 'WORKSPACE_ID i KBC_WORKSPACE_MANIFEST_PATH chybí'
    if not os.path.isfile(manifest_path):
        return None, f'Manifest {manifest_path} neexistuje'
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return None, f'Manifest {manifest_path} není validní JSON: {e}'
    except OSError as e:
        return None, f'Manifest {manifest_path} nelze přečíst: {e}'

    workspace_id = manifest.get('workspaceId')
    if not workspace_id:
        return None, f'Manifest {manifest_path} neobsahuje klíč workspaceId'
    return str(workspace_id), f'manifest {manifest_path}'


def render_dsa_status() -> None:
    """Render the Direct Storage Access (DSA) status checklist."""
    st.header('Direct Storage Access (DSA)')
    st.caption('Kontrola, zda je pro tuto data appku zapnutý a funkční přímý přístup do Storage.')

    failed_steps: list[str] = []

    # Step 1 — required environment variables
    required_vars = ['BRANCH_ID', 'QUERY_SERVICE_URL', 'KBC_TOKEN']
    missing = [var for var in required_vars if not os.environ.get(var)]
    has_workspace_source = bool(
        os.environ.get('WORKSPACE_ID') or os.environ.get('KBC_WORKSPACE_MANIFEST_PATH')
    )
    if not has_workspace_source:
        missing.append('WORKSPACE_ID nebo KBC_WORKSPACE_MANIFEST_PATH')

    if missing:
        st.error(f'1. Proměnné prostředí — chybí: {", ".join(missing)}')
        failed_steps.append('env')
    else:
        st.success('1. Proměnné prostředí — všechny povinné jsou nastavené')

    # Step 2 — workspace id resolution
    workspace_id, source = _resolve_workspace_id()
    if workspace_id:
        st.success(f'2. Workspace ID — nalezeno ({_mask(workspace_id)}), zdroj: {source}')
    else:
        st.error(f'2. Workspace ID — nepodařilo se zjistit: {source}')
        failed_steps.append('workspace')

    # Step 3 — Query Service connectivity (SELECT 1)
    client = None
    if missing or not workspace_id:
        st.warning('3. Konektivita Query Service — přeskočeno (chybí předchozí kroky)')
        failed_steps.append('connectivity')
    else:
        try:
            import keboola_query_service

            client = keboola_query_service.Client(
                url=os.environ['QUERY_SERVICE_URL'],
                token=os.environ['KBC_TOKEN'],
            )
            client.query(workspace_id, 'SELECT 1')
            st.success('3. Konektivita Query Service — SELECT 1 proběhl úspěšně')
        except ImportError as e:
            st.error(f'3. Konektivita Query Service — chybí balíček keboola_query_service: {e}')
            failed_steps.append('connectivity')
            client = None
        except Exception as e:
            st.error(f'3. Konektivita Query Service — selhalo: {e}')
            failed_steps.append('connectivity')
            client = None

    # Step 4 — table access
    if client is None:
        st.warning('4. Přístup k tabulkám — přeskočeno (konektivita neprošla)')
        failed_steps.append('tables')
    else:
        try:
            result = client.query(
                workspace_id,
                'SELECT * FROM INFORMATION_SCHEMA.TABLES LIMIT 1',
            )
            try:
                row_count = len(result)
            except TypeError:
                row_count = 'neznámý počet'
            st.success(f'4. Přístup k tabulkám — dotaz proběhl, viditelných řádků: {row_count}')
        except Exception as e:
            st.error(f'4. Přístup k tabulkám — selhalo: {e}')
            failed_steps.append('tables')

    # Overall summary
    if not failed_steps:
        st.success('✅ DSA je zapnutý a funkční.')
    else:
        st.error('❌ DSA není plně funkční — viz kroky výše a možné příčiny níže.')

    # Env dump — names only, never values
    with st.expander('Env dump (pouze názvy, bez hodnot)'):
        env_vars = [
            'BRANCH_ID',
            'QUERY_SERVICE_URL',
            'KBC_TOKEN',
            'WORKSPACE_ID',
            'KBC_WORKSPACE_MANIFEST_PATH',
        ]
        for var in env_vars:
            state = '<set>' if os.environ.get(var) else '<missing>'
            st.write(f'{var}: {state}')

    # Hints — only when something failed
    if failed_steps:
        with st.expander('Možné příčiny'):
            if 'env' in failed_steps or 'workspace' in failed_steps:
                st.markdown(
                    '- Na úrovni projektu není zapnutá feature **`data-apps-storage-workspace`** '
                    '(jiná věc než přepínač u konkrétní appky).\n'
                    '- V **Advanced Settings** appky není zapnutý **Storage Access**, '
                    'nebo nejsou vybrané žádné zapisovatelné tabulky.\n'
                    '- Appka nebyla po zapnutí DSA **znovu nasazená** — workspace vzniká až při deployi.\n'
                    '- `KBC_WORKSPACE_MANIFEST_PATH` ukazuje na neexistující nebo poškozený JSON.'
                )
            if 'connectivity' in failed_steps:
                st.markdown(
                    '- `QUERY_SERVICE_URL` míří na `connection.keboola.com` místo na '
                    '`query.keboola.com`.\n'
                    '- Příliš stará verze image — vyžaduje **Streamlit ≥ 1.17.0** '
                    'nebo **Python-JS ≥ 1.1.0**.\n'
                    '- Běh na **BigQuery** stacku — DSA je zatím jen pro **Snowflake**.\n'
                    '- Neplatný nebo expirovaný `KBC_TOKEN`.'
                )
            if 'tables' in failed_steps:
                st.markdown(
                    '- Ve **Storage Access** nejsou vybrané žádné tabulky, '
                    'takže workspace nic nevidí.\n'
                    '- Appka nebyla po změně výběru tabulek znovu nasazená.'
                )


def render_file_preview(file_path: str) -> None:
    """Render a preview of the file based on its extension."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.csv':
            st.dataframe(pd.read_csv(file_path))
        elif ext == '.tsv':
            st.dataframe(pd.read_csv(file_path, sep='\t'))
        elif ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                st.json(json.load(f))
        elif ext == '.toml':
            st.write(toml.load(file_path))
        elif ext in ('.txt', '.log', '.md', '.yaml', '.yml', '.xml', '.html', '.py', '.sql', '.ini', '.cfg', '.conf'):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                st.code(f.read(), language=ext.lstrip('.') or None)
        else:
            size = os.path.getsize(file_path)
            st.info(f'Náhled pro příponu {ext or "(žádná)"} není podporován. Velikost: {size} B.')
    except Exception as e:
        st.error(f'Chyba při čtení souboru: {e}')

tabs = st.tabs(["Hello world", "Debug", "DSA"])

with tabs[0]:
    st.header("Hello World App")
    st.write("Hello, world! Toto je tvoje první aplikace ve Streamlit.")

    name = st.text_input("Zadej své jméno:")

    if st.button("Pozdrav"):
        st.write(f"Ahoj, {name}!")

with tabs[1]:
    st.header("Debug")
    st.title('Python version')
    st.write(sys.version)

    config_file_path = os.path.join(os.path.dirname(__file__), os.path.pardir, '.streamlit', 'config.toml')
    secrets_file_path = os.path.join(os.path.dirname(__file__), os.path.pardir, '.streamlit', 'secrets.toml')

    st.title('Current path')
    st.write(os.path.dirname(__file__))

    st.title('Current working directory')
    st.write(os.getcwd())

    display_toml_content('Obsah config.toml', config_file_path)
    display_toml_content('Obsah secrets.toml', secrets_file_path)

    st.title('Installed packages')
    for dist in importlib.metadata.distributions():
        st.write(dist.metadata["Name"], dist.version)

    st.title('Soubory v /data')
    data_path = '/data'
    if os.path.isdir(data_path):
        files = []
        for root, _, filenames in os.walk(data_path):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        if files:
            for file_path in sorted(files):
                with st.expander(file_path):
                    render_file_preview(file_path)
        else:
            st.write(f'Složka {data_path} je prázdná.')
    else:
        st.error(f'Složka {data_path} neexistuje.')

with tabs[2]:
    render_dsa_status()

