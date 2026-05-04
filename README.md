# PBI_AzureDevops_deploymentPipelines

# Power BI CI/CD Pipeline

Automated CI/CD pipeline for Power BI reports stored in **PBIP (Power BI Project)** format, using Azure DevOps and Microsoft's official [`fabric-cicd`](https://microsoft.github.io/fabric-cicd/latest/) library.

Merging a pull request to `main` automatically validates and deploys your PBIP files to a single Fabric workspace — no manual publishing required.

---

## How it works

```
Developer opens Pull Request (feature branch → main)
        ↓
azure-pipelines.yml triggers automatically (branch policy)
  ├─ Job 1: Build_Datasets — Tabular Editor BPA rules on .pbism files
  └─ Job 2: Build_Reports  — PBI Inspector rules on .pbir files
        ↓
All rules pass → PR approved and merged to main
        ↓
deployToWorkspace.yml triggers automatically (merge to main)
        ↓
fabric-cicd publishes .SemanticModel and .Report folders to Fabric workspace
```

---

## Repository structure

```

├── deployToWorkspace.yml       # CD pipeline — deploys on merge to main
├── azure-pipelines.yml         # CI pipeline — validates on every PR
├── deploy.py                   # Python deploy script (used by deployToWorkspace.yml)
├── Rules-Dataset.json          # Optional: custom Tabular Editor BPA rules
├── Rules-Report.json           # Optional: custom PBI Inspector rules
├── YourReport.Report/
│   ├── definition.pbir
│   └── definition/
│       └── pages/
└── YourReport.SemanticModel/
    ├── definition.pbism
    └── definition/
        ├── model.tmdl
        └── tables/
```

> **Note:** `Rules-Dataset.json` and `Rules-Report.json` are optional. If absent, both pipelines automatically download the latest default rules from the official Microsoft and PBI Inspector repositories.

---

## Prerequisites

| Requirement | Details |
|---|---|
| Power BI workspace | Premium Per User (PPU), Premium (P SKU), or Fabric capacity |
| Azure DevOps | Any tier — free tier works |
| Python | 3.9–3.12 (installed automatically on the pipeline agent) |
| PBIP format | Reports saved as `.pbip` folders, **not** `.pbix` files |
| Azure subscription | Needed to create the service connection (Reader role minimum) |
| Fabric workspace role | Service principal needs **Contributor** or **Admin** on the workspace |

---

## Pipeline overview

### [`deployToWorkspace.yml`](deployToWorkspace.yml) — CD pipeline

Triggers on every merge to `main`. Uses `AzureCLI@2` to authenticate via service connection, then runs `deploy.py` which calls `fabric-cicd` to publish all PBIP items to the target workspace.

```yaml
trigger:
  branches:
    include:
      - main

pr: none
```

**What it does:**
- Checks out the repo
- Installs Python 3.12 and `fabric-cicd`
- Authenticates using the Azure service connection (credentials stored securely — never in the YAML)
- Publishes all `.SemanticModel` and `.Report` folders to the configured workspace

**Pipeline variable required:**

| Variable | Description | Secret? |
|---|---|---|
| `workspaceId` | GUID of your target Fabric workspace | No |

---

### [`azure-pipelines.yml`](azure-pipelines.yml) — CI pipeline

Triggers on every pull request via branch policy. Runs two parallel jobs to validate PBIP quality before allowing a merge.

```yaml
trigger: none
# triggered by branch policy build validation rule, not by a branch push
```

**Job 1 — `Build_Datasets`**
- Downloads [Tabular Editor](https://github.com/TabularEditor/TabularEditor) portable binaries
- Downloads [Microsoft BPA rules](https://github.com/microsoft/Analysis-Services/tree/master/BestPracticeRules) (or uses `Rules-Dataset.json` from repo root if present)
- Runs Best Practice Analyzer against every `.pbism` and `.pbidataset` file in the repo

**Job 2 — `Build_Reports`**
- Downloads [PBI Inspector](https://github.com/NatVanG/PBI-Inspector) CLI binaries
- Downloads [base rules](https://github.com/NatVanG/PBI-Inspector/blob/main/Rules/Base-rules.json) (or uses `Rules-Report.json` from repo root if present)
- Runs report quality checks against every `.pbir` file in the repo

> A high-severity rule failure in either job **blocks the PR merge**.

---

## Setup

### 1. Create a service principal

In [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **New registration**:

```
Name:                  PowerBI-DevOps-SP
Supported account type: Single tenant
Redirect URI:          leave blank
```

After registering, copy:
- **Application (client) ID**
- **Directory (tenant) ID**

Then go to **Certificates & secrets** → **New client secret** → copy the **Value** (not the Secret ID).

---

### 2. Grant permissions

**Power BI Admin Portal** → **Tenant settings** → enable:
```
Service principals can call Fabric public APIs → Enabled (entire organisation)
```

**Fabric workspace** → **Manage access** → add `PowerBI-DevOps-SP` with **Contributor** role.

**Azure Portal** → your subscription → **Access control (IAM)** → **Add role assignment** → assign **Reader** to `PowerBI-DevOps-SP`.

---

### 3. Create the Azure DevOps service connection

**Project Settings** → **Service connections** → **New service connection** → **Azure Resource Manager** → **App registration (manual)** → **Secret**:

```
Subscription ID:      your-azure-subscription-id
Service Principal Id: your-application-client-id
Service principal key: your-client-secret-value
Tenant ID:            your-directory-tenant-id
Name:                 your-azure-service-connection
```

> The name you give this connection must match the `azureSubscription:` value in [`deployToWorkspace.yml`](deployToWorkspace.yml).

---

### 4. Add pipeline variable

In Azure DevOps → your `deployToWorkspace.yml` pipeline → **Edit** → **Variables**:

```
Name:    workspaceId
Value:   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Secret:  No
```

Find your workspace ID in the Fabric portal URL:
```
https://app.fabric.microsoft.com/groups/YOUR-WORKSPACE-ID/...
```

---

### 5. Create the pipelines in Azure DevOps

**deployToWorkspace.yml:**
1. Pipelines → **New pipeline** → Azure Repos Git → your repo
2. Select **Existing Azure Pipelines YAML file** → path: `deployToWorkspace.yml`
3. Save (do not run yet)

**azure-pipelines.yml:**
1. Pipelines → **New pipeline** → Azure Repos Git → your repo
2. Select **Existing Azure Pipelines YAML file** → path: `azure-pipelines.yml`
3. Save

---

### 6. Set branch policies on main

**Repos** → **Branches** → `main` → **...** → **Branch policies**:

**Reviewer policy:**
```
Require a minimum number of reviewers: ON
Minimum reviewers:                      1
Allow requestors to approve own changes: OFF
```

**Build validation — CI:**
```
Pipeline:     azure-pipelines.yml
Trigger:      Automatic
Requirement:  Required
Display name: Validate PBIP quality
```

**Build validation — CD preview:**
```
Pipeline:     deployToWorkspace.yml
Trigger:      Automatic
Requirement:  Optional
Display name: Deploy PBIP (preview)
```

---

## Customising validation rules

To override the default rules, add these files to the **repo root**:

| File | Overrides |
|---|---|
| `Rules-Dataset.json` | Tabular Editor BPA rules for semantic models |
| `Rules-Report.json` | PBI Inspector rules for reports |

If these files are not present, both pipelines download and use the latest official rules automatically on every run.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `does not have authorization to perform action subscriptions/read` | Service principal missing Reader role on Azure subscription. See [Setup step 2](#2-grant-permissions). |
| `Service principal not found` | Wrong ID used — ensure you copied **Application (client) ID**, not the Object ID. |
| `fabric-cicd not found` | `UsePythonVersion@0` task missing from YAML or Python version below 3.9. |
| `Workspace not found or access denied` | Service principal not added to the Fabric workspace. See [Setup step 2](#2-grant-permissions). |
| `Pipeline does not trigger on merge` | Confirm `trigger: branches: include: - main` is at the top of `deployToWorkspace.yml` and `pr: none` is present. |
| `Git conflict in Fabric portal` | Disconnect Fabric Git Integration from the workspace — it conflicts with `fabric-cicd`. Do not use both on the same workspace. |
| `Data source credentials error (first deploy only)` | Expected on first run. Go to Workspace → semantic model → **Settings** → **Data source credentials** and configure once manually. |

---

## References

- [`fabric-cicd` documentation](https://microsoft.github.io/fabric-cicd/latest/)
- [Microsoft Learn — Deploy PBIP using fabric-cicd](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-deploy-fabric-cicd)
- [Microsoft Learn — Azure DevOps build pipeline integration with PBIP](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-build-pipelines)
- [Azure DevOps service connections](https://learn.microsoft.com/en-us/azure/devops/pipelines/library/connect-to-azure)
- [Tabular Editor BPA rules](https://github.com/microsoft/Analysis-Services/tree/master/BestPracticeRules)
- [PBI Inspector](https://github.com/NatVanG/PBI-Inspector)
- [`fabric-cicd` GitHub repository](https://github.com/microsoft/fabric-cicd)