import json
import subprocess

commands = {'aws': ['aws', '--version'], 'bash': ['bash', '--version'], 'jq': ['jq', '--version'], 'python': ['python3', '--version'], 'pip': ['python3', '-m', 'pip', '--version'], 'node': ['node', '--version'], 'npm': ['npm', '--version'], 'yarn': ['yarn', '--version'], 'git': ['git', '--version'], 'docker': ['docker', '--version'], 'buildx': ['docker', 'buildx', 'version'], 'ruby': ['ruby', '--version'], 'go': ['go', 'version'], 'java': ['java', '-version'], 'dotnet': ['dotnet', '--version']}
versions = {name: subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).splitlines()[0] for name, command in commands.items()}
print('CI_BUILDER_TOOL_VERSIONS=' + json.dumps(versions))
