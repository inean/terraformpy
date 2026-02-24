"""Minimal runtime client examples for execute-mode integrations."""

from terraformpy import Client, TerraformPy


# Constructor shapes
client = Client()
client = Client(cwd="infra/vm")
client = Client(working_dir="infra/vm")
client = TerraformPy(chdir="infra/vm")

# plan call shapes
rc = client.plan(var_file="vm.tfvars", out="vm.plan", input=False, no_color=True)
rc = client.plan(var_file="vm.tfvars", out="vm.plan")
rc = client.plan("-var-file=vm.tfvars", "-out=vm.plan", "-input=false", "-no-color")

# apply call shapes
rc = client.apply(plan="vm.plan", auto_approve=True, input=False, no_color=True)
rc = client.apply(plan="vm.plan", auto_approve=True)
rc = client.apply("vm.plan")
rc = client.apply("-auto-approve", "vm.plan")

# destroy call shapes
rc = client.destroy(var={"vm_name": "vm-1"}, auto_approve=True, input=False, no_color=True)
rc = client.destroy(var="vm_name=vm-1", auto_approve=True)
rc = client.destroy("-auto-approve", "-var=vm_name=vm-1")

# output call shapes
outputs = client.output(json=True)
outputs = client.output("-json")
outputs = client.output()

if rc != 0:
    raise SystemExit(rc)

print(outputs)
