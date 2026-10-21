import json
import os
import re
import subprocess

binaries, modules = [], []
root_device = os.stat('/').st_dev
for directory, dirs, files in os.walk('/', topdown=True, followlinks=False):
    dirs[:] = [d for d in dirs if os.lstat(os.path.join(directory, d)).st_dev == root_device and os.path.join(directory, d) not in ('/proc', '/sys', '/dev')]
    for name in files:
        path = os.path.join(directory, name)
        if re.fullmatch(r'php(?:-cgi|-fpm|dbg)?[0-9.]*|php[0-9.]+(?:-cgi|-fpm)', name):
            binaries.append(path)
        if re.fullmatch(r'libphp.*\.so(?:\..*)?', name) or ('.so' in name and re.search(r'/php[0-9.]*/(?:modules|extensions)(?:/|$)', path)):
            modules.append(path)
packages = subprocess.check_output(['rpm', '-qa', '--qf', '%{NAME}\n'], text=True).splitlines()
packages = [p for p in packages if re.match(r'^php(?:[0-9]*-|$)', p)]
assert not binaries and not modules and not packages, 'PHP runtime/module/package remains in standalone builder'
tools = {}
for name, command in {'aws': ['aws', '--version'], 'bash': ['bash', '--version'], 'jq': ['jq', '--version'], 'python': ['python3', '--version'], 'pip': ['python3', '-m', 'pip', '--version'], 'node': ['node', '--version'], 'npm': ['npm', '--version'], 'yarn': ['yarn', '--version'], 'git': ['git', '--version'], 'docker': ['docker', '--version'], 'buildx': ['docker', 'buildx', 'version'], 'envsubst': ['envsubst', '--version']}.items():
    tools[name] = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).splitlines()[0]
assert subprocess.check_output(['envsubst'], input='${CI_BUILDER_TEMPLATE_VALUE}', env={**os.environ,'CI_BUILDER_TEMPLATE_VALUE':'builder-proof'}, text=True)=='builder-proof'
assert subprocess.check_output(['aws','sts','get-caller-identity','--query','Account','--output','text'],text=True).strip()=='950664063715'
tools['aws_sts_account']='950664063715'
subprocess.run(['n', '--offline', os.environ['NODE_22_VERSION']], check=True, stdout=subprocess.DEVNULL)
assert subprocess.check_output(['node', '--version'], text=True).strip().startswith('v22.')
tools['node22'] = subprocess.check_output(['node', '--version'], text=True).strip()
tools['node22_yarn'] = subprocess.check_output(['yarn', '--version'], text=True).strip()
subprocess.run(['docker', 'info'], check=True, stdout=subprocess.DEVNULL)
print('CI_BUILDER_LAUNCH_PROOF=' + json.dumps({'php_binaries': binaries, 'php_modules': modules, 'php_packages': packages, 'tools': tools, 'docker_daemon': 'passed'}))
