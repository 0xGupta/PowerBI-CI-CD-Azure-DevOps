import argparse
from azure.identity import AzureCliCredential
from fabric_cicd import FabricWorkspace, publish_all_items

parser = argparse.ArgumentParser()
parser.add_argument("--workspace_id", type=str, required=True)
args = parser.parse_args()

credential = AzureCliCredential()

workspace = FabricWorkspace(
    workspace_id       = args.workspace_id,
    repository_directory = ".",
    item_type_in_scope = ["SemanticModel", "Report"],
    token_credential   = credential,
)

publish_all_items(workspace)