// ============================================================
// Vandelay Banking Corporation - Migration Knowledge Graph
// ============================================================
// 
// VMware OpenShift to BareMetal OpenShift Migration Data
//
// This file contains sample data for demonstrating the Migration
// Assistant agent capabilities. It includes:
//
// - 10 application namespaces
// - 4 source clusters (VMware OpenShift)
// - 4 destination clusters (BareMetal OpenShift)
// - Cluster configurations (VIPs, infra nodes, SSO)
// - EgressIP mappings
// - Migration phases and timeline
// - Migration tasks with ownership
// - CD tool types
// - Storage class mappings
//
// Usage:
//   python -m data_ingestion.ingest_migration_graph --clear
//
// ============================================================


// ============================================================
// 1. MIGRATION PHASES
// ============================================================
// Timeline: DEV → UAT → PROD (3 waves)

CREATE (phase_dev:MigrationPhase {
  id: 'PHASE-DEV',
  name: 'DEV',
  description: 'Development environment migration',
  start_date: date('2026-01-05'),
  end_date: date('2026-02-28'),
  status: 'active'
});

CREATE (phase_uat:MigrationPhase {
  id: 'PHASE-UAT',
  name: 'UAT',
  description: 'User acceptance testing environment migration',
  start_date: date('2026-04-01'),
  end_date: date('2026-05-31'),
  status: 'upcoming'
});

CREATE (phase_prod_w1:MigrationPhase {
  id: 'PHASE-PROD-W1',
  name: 'PROD_W1',
  description: 'Production wave 1 - critical applications',
  start_date: date('2026-07-01'),
  end_date: date('2026-08-31'),
  status: 'upcoming'
});

CREATE (phase_prod_w2:MigrationPhase {
  id: 'PHASE-PROD-W2',
  name: 'PROD_W2',
  description: 'Production wave 2 - standard applications',
  start_date: date('2026-10-01'),
  end_date: date('2026-11-30'),
  status: 'upcoming'
});

CREATE (phase_prod_w3:MigrationPhase {
  id: 'PHASE-PROD-W3',
  name: 'PROD_W3',
  description: 'Production wave 3 - remaining applications',
  start_date: date('2027-01-05'),
  end_date: date('2027-02-28'),
  status: 'upcoming'
});


// ============================================================
// 2. SOURCE CLUSTERS (VMware OpenShift)
// ============================================================

CREATE (src_east_dev:SourceCluster {
  id: 'VMWARE-EAST-DEV-1',
  name: 'VMWARE-EAST-DEV-1',
  type: 'VMware OpenShift',
  platform: 'vSphere',
  data_center: 'DC-EAST',
  region: 'EAST',
  openshift_version: '4.12'
});

CREATE (src_east_uat:SourceCluster {
  id: 'VMWARE-EAST-UAT-1',
  name: 'VMWARE-EAST-UAT-1',
  type: 'VMware OpenShift',
  platform: 'vSphere',
  data_center: 'DC-EAST',
  region: 'EAST',
  openshift_version: '4.12'
});

CREATE (src_west_dev:SourceCluster {
  id: 'VMWARE-WEST-DEV-1',
  name: 'VMWARE-WEST-DEV-1',
  type: 'VMware OpenShift',
  platform: 'vSphere',
  data_center: 'DC-WEST',
  region: 'WEST',
  openshift_version: '4.12'
});

CREATE (src_west_uat:SourceCluster {
  id: 'VMWARE-WEST-UAT-1',
  name: 'VMWARE-WEST-UAT-1',
  type: 'VMware OpenShift',
  platform: 'vSphere',
  data_center: 'DC-WEST',
  region: 'WEST',
  openshift_version: '4.12'
});


// ============================================================
// 3. DESTINATION CLUSTERS (BareMetal OpenShift)
// ============================================================

CREATE (dest_east_dev:DestinationCluster {
  id: 'BAREMETAL-EAST-DEV',
  name: 'BAREMETAL-EAST-DEV',
  type: 'BareMetal OpenShift',
  platform: 'Physical',
  data_center: 'DC-EAST',
  region: 'EAST',
  subnet: '10.100.0.0/16',
  openshift_version: '4.14'
});

CREATE (dest_east_uat:DestinationCluster {
  id: 'BAREMETAL-EAST-UAT',
  name: 'BAREMETAL-EAST-UAT',
  type: 'BareMetal OpenShift',
  platform: 'Physical',
  data_center: 'DC-EAST',
  region: 'EAST',
  subnet: '10.101.0.0/16',
  openshift_version: '4.14'
});

CREATE (dest_west_dev:DestinationCluster {
  id: 'BAREMETAL-WEST-DEV',
  name: 'BAREMETAL-WEST-DEV',
  type: 'BareMetal OpenShift',
  platform: 'Physical',
  data_center: 'DC-WEST',
  region: 'WEST',
  subnet: '10.200.0.0/16',
  openshift_version: '4.14'
});

CREATE (dest_west_uat:DestinationCluster {
  id: 'BAREMETAL-WEST-UAT',
  name: 'BAREMETAL-WEST-UAT',
  type: 'BareMetal OpenShift',
  platform: 'Physical',
  data_center: 'DC-WEST',
  region: 'WEST',
  subnet: '10.201.0.0/16',
  openshift_version: '4.14'
});


// ============================================================
// 4. CLUSTER CONFIGURATIONS
// ============================================================
// Each destination cluster has VIP, infra nodes, and SSO config

CREATE (cfg_east_dev:ClusterConfig {
  id: 'CFG-BAREMETAL-EAST-DEV',
  vip_name: 'baremetal-east-dev-vip.vandelay.internal',
  vip_ip_address: '10.100.1.10',
  infra_node_ips: ['10.100.2.1', '10.100.2.2', '10.100.2.3'],
  sso_reghost_hostname: 'sso-east-dev.vandelay.internal',
  sso_shared_secret_ref: 'vault:secret/sso/baremetal-east-dev',
  wildcard_dns: 'apps.baremetal-east-dev.vandelay.internal'
});

CREATE (cfg_east_uat:ClusterConfig {
  id: 'CFG-BAREMETAL-EAST-UAT',
  vip_name: 'baremetal-east-uat-vip.vandelay.internal',
  vip_ip_address: '10.101.1.10',
  infra_node_ips: ['10.101.2.1', '10.101.2.2', '10.101.2.3'],
  sso_reghost_hostname: 'sso-east-uat.vandelay.internal',
  sso_shared_secret_ref: 'vault:secret/sso/baremetal-east-uat',
  wildcard_dns: 'apps.baremetal-east-uat.vandelay.internal'
});

CREATE (cfg_west_dev:ClusterConfig {
  id: 'CFG-BAREMETAL-WEST-DEV',
  vip_name: 'baremetal-west-dev-vip.vandelay.internal',
  vip_ip_address: '10.200.1.10',
  infra_node_ips: ['10.200.2.1', '10.200.2.2', '10.200.2.3'],
  sso_reghost_hostname: 'sso-west-dev.vandelay.internal',
  sso_shared_secret_ref: 'vault:secret/sso/baremetal-west-dev',
  wildcard_dns: 'apps.baremetal-west-dev.vandelay.internal'
});

CREATE (cfg_west_uat:ClusterConfig {
  id: 'CFG-BAREMETAL-WEST-UAT',
  vip_name: 'baremetal-west-uat-vip.vandelay.internal',
  vip_ip_address: '10.201.1.10',
  infra_node_ips: ['10.201.2.1', '10.201.2.2', '10.201.2.3'],
  sso_reghost_hostname: 'sso-west-uat.vandelay.internal',
  sso_shared_secret_ref: 'vault:secret/sso/baremetal-west-uat',
  wildcard_dns: 'apps.baremetal-west-uat.vandelay.internal'
});


// ============================================================
// 5. EGRESS IPS
// ============================================================
// Source (VMware) and Destination (BareMetal) egress IPs

// EAST DEV source egress IPs
CREATE (egress_src_east_dev_1:EgressIP {
  id: 'EGRESS-VMWARE-EAST-DEV-1',
  ip_address: '192.168.10.50',
  cluster_id: 'VMWARE-EAST-DEV-1',
  ip_type: 'source'
});

CREATE (egress_src_east_dev_2:EgressIP {
  id: 'EGRESS-VMWARE-EAST-DEV-2',
  ip_address: '192.168.10.51',
  cluster_id: 'VMWARE-EAST-DEV-1',
  ip_type: 'source'
});

// EAST DEV destination egress IPs
CREATE (egress_dest_east_dev_1:EgressIP {
  id: 'EGRESS-BAREMETAL-EAST-DEV-1',
  ip_address: '10.100.50.10',
  cluster_id: 'BAREMETAL-EAST-DEV',
  ip_type: 'destination'
});

CREATE (egress_dest_east_dev_2:EgressIP {
  id: 'EGRESS-BAREMETAL-EAST-DEV-2',
  ip_address: '10.100.50.11',
  cluster_id: 'BAREMETAL-EAST-DEV',
  ip_type: 'destination'
});

// WEST DEV source egress IPs
CREATE (egress_src_west_dev_1:EgressIP {
  id: 'EGRESS-VMWARE-WEST-DEV-1',
  ip_address: '192.168.20.50',
  cluster_id: 'VMWARE-WEST-DEV-1',
  ip_type: 'source'
});

CREATE (egress_src_west_dev_2:EgressIP {
  id: 'EGRESS-VMWARE-WEST-DEV-2',
  ip_address: '192.168.20.51',
  cluster_id: 'VMWARE-WEST-DEV-1',
  ip_type: 'source'
});

// WEST DEV destination egress IPs
CREATE (egress_dest_west_dev_1:EgressIP {
  id: 'EGRESS-BAREMETAL-WEST-DEV-1',
  ip_address: '10.200.50.10',
  cluster_id: 'BAREMETAL-WEST-DEV',
  ip_type: 'destination'
});

CREATE (egress_dest_west_dev_2:EgressIP {
  id: 'EGRESS-BAREMETAL-WEST-DEV-2',
  ip_address: '10.200.50.11',
  cluster_id: 'BAREMETAL-WEST-DEV',
  ip_type: 'destination'
});


// ============================================================
// 6. CD TOOL TYPES
// ============================================================

CREATE (cd_tool_a:CDToolType {
  id: 'CD-TOOL-A',
  name: 'Enterprise CD Platform',
  description: 'Modern enterprise continuous delivery platform with GitOps support',
  supports_gitops: true
});

CREATE (cd_tool_b:CDToolType {
  id: 'CD-TOOL-B',
  name: 'Legacy CD Platform',
  description: 'Traditional CD platform with pipeline-based deployments',
  supports_gitops: false
});

CREATE (cd_tool_c:CDToolType {
  id: 'CD-TOOL-C',
  name: 'Release Management Tool',
  description: 'Enterprise release management and deployment orchestration',
  supports_gitops: false
});


// ============================================================
// 7. STORAGE CLASSES
// ============================================================

// Source (VMware) storage classes
CREATE (sc_thin:StorageClass {
  id: 'SC-THIN',
  name: 'thin',
  provisioner: 'kubernetes.io/vsphere-volume',
  platform: 'source',
  is_default: false,
  notes: 'Legacy vSphere storage - not available on BareMetal'
});

CREATE (sc_thin_csi:StorageClass {
  id: 'SC-THIN-CSI',
  name: 'thin-csi',
  provisioner: 'csi.vsphere.vmware.com',
  platform: 'source',
  is_default: true,
  notes: 'vSphere CSI driver - not available on BareMetal'
});

// Destination (BareMetal) storage classes
CREATE (sc_dell:StorageClass {
  id: 'SC-DELL-CSM',
  name: 'dell-csm-sc',
  provisioner: 'csi-vxflexos.dellemc.com',
  platform: 'destination',
  is_default: false,
  notes: 'Dell CSM storage for BareMetal clusters'
});

CREATE (sc_ontap:StorageClass {
  id: 'SC-ONTAP-NAS',
  name: 'sc-ontap-nas',
  provisioner: 'csi.trident.netapp.io',
  platform: 'destination',
  is_default: true,
  notes: 'NetApp ONTAP NAS storage - default for BareMetal'
});


// ============================================================
// 8. MIGRATION TASKS
// ============================================================
// Complete catalog of migration tasks with ownership

// Platform Ops automated tasks
CREATE (task_project_copy:MigrationTask {
  id: 'TASK-001',
  name: 'Project and Resource Copy',
  category: 'infrastructure',
  owner: 'platform_ops',
  is_automated: true,
  requires_service_request: false,
  sequence_order: 1,
  description: 'Platform Ops copies projects and essential resources (quota, limits, service accounts, role bindings, secrets, network policies, EgressIP, persistent volumes, and persistent volume claims) from source cluster to destination cluster.'
});

CREATE (task_netgroup:MigrationTask {
  id: 'TASK-002',
  name: 'Custom Netgroup Configuration',
  category: 'infrastructure',
  owner: 'platform_ops',
  is_automated: true,
  requires_service_request: false,
  sequence_order: 2,
  description: 'Platform Ops ensures destination cluster application nodes are added to appropriate custom netgroups.'
});

CREATE (task_firewall_auto:MigrationTask {
  id: 'TASK-003',
  name: 'Internet EgressIP Firewall Rules',
  category: 'network',
  owner: 'platform_ops',
  is_automated: true,
  requires_service_request: false,
  sequence_order: 3,
  description: 'Firewall rules for internet-bound EgressIP traffic are automatically recreated for destination cluster. Note: Old cluster rules must be manually deleted after migration.'
});

// App Team manual tasks - prerequisites
CREATE (task_identify_internal:MigrationTask {
  id: 'TASK-004',
  name: 'Identify Internal System Connectivity',
  category: 'prerequisite',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: true,
  service_request_type: 'firewall',
  sequence_order: 4,
  estimated_lead_time: '14 days',
  description: 'Identify where EgressIPs are used for connectivity to INTERNAL systems (databases, SFTP, message queues, mainframes). Submit firewall requests for new destination EgressIPs.'
});

CREATE (task_vanity_url:MigrationTask {
  id: 'TASK-005',
  name: 'Implement Vanity URL',
  category: 'prerequisite',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: true,
  service_request_type: 'dns',
  sequence_order: 5,
  estimated_lead_time: '7 days',
  description: 'Consider implementing a Vanity URL to ease future migrations and improve application functionality. Strongly recommended for all applications.'
});

// App Team - security tasks
CREATE (task_certificates:MigrationTask {
  id: 'TASK-006',
  name: 'Certificate Changes',
  category: 'security',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: true,
  service_request_type: 'certificate',
  sequence_order: 6,
  estimated_lead_time: '7 days',
  description: 'If using cluster-based routes in certificate SAN list, request new certificates for destination cluster. Update certificate references in application configuration. No action needed if only Vanity URL in SAN list.'
});

CREATE (task_secrets:MigrationTask {
  id: 'TASK-007',
  name: 'Secrets Migration',
  category: 'security',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 7,
  description: 'Review secrets in destination namespace. Managed and unmanaged secrets through Secrets API require no action. Native secrets are copied automatically.'
});

CREATE (task_sso:MigrationTask {
  id: 'TASK-008',
  name: 'SSO Configuration',
  category: 'security',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: true,
  service_request_type: 'sso',
  sequence_order: 8,
  estimated_lead_time: '7 days',
  description: 'Register application with SSO provider on destination cluster. Update SSO_REGHOST_HOSTNAME environment variable. If using Vanity URL, no base URL changes needed. If using cluster route, submit modification request.'
});

// App Team - network tasks
CREATE (task_network_policy:MigrationTask {
  id: 'TASK-009',
  name: 'Network Policy Changes',
  category: 'network',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 9,
  description: 'Review and update network policies if they reference specific IP ranges. Policies are copied but may need adjustment for new network topology.'
});

CREATE (task_proxy:MigrationTask {
  id: 'TASK-010',
  name: 'Proxy Configuration Update',
  category: 'network',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 10,
  description: 'Update proxy port from 9999 (DEV/UAT) or 7777 (PROD) to 17777 for BareMetal clusters. Update application configuration accordingly.'
});

// App Team - storage tasks
CREATE (task_storage:MigrationTask {
  id: 'TASK-011',
  name: 'Storage Class Migration',
  category: 'storage',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 11,
  description: 'Update PVC definitions to use new storage classes. Change from thin/thin-csi to dell-csm-sc or sc-ontap-nas. Dynamic storage from source cannot be reused; redeploy product-specific operators (Redis, databases, etc.).'
});

// App Team - deployment tasks
CREATE (task_cd_update:MigrationTask {
  id: 'TASK-012',
  name: 'CD Pipeline Update',
  category: 'deployment',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 12,
  description: 'Update CD tool configuration to target destination cluster. Add namespace, create environment, modify manifest or create new pipeline as needed. Steps vary by CD tool type.'
});

CREATE (task_deployment:MigrationTask {
  id: 'TASK-013',
  name: 'Application Deployment',
  category: 'deployment',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 13,
  description: 'Deploy application resources (Deployments, Services, Routes, HPAs) on destination cluster via CD pipeline. Resources deployed via CD are intentionally omitted from automatic copy.'
});

// App Team - operators (if needed)
CREATE (task_operators:MigrationTask {
  id: 'TASK-014',
  name: 'Operator Installation',
  category: 'operators',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: true,
  service_request_type: 'incident',
  sequence_order: 14,
  description: 'For applications using Redis, Couchbase, Service Mesh, or other operators: raise ticket with Platform Ops for operator installation on destination cluster. Provide namespace and configuration requirements.'
});

// App Team - validation and cleanup
CREATE (task_validation:MigrationTask {
  id: 'TASK-015',
  name: 'Application Validation',
  category: 'validation',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: false,
  sequence_order: 15,
  description: 'Perform application checkouts: health checks, smoke tests, integration tests, performance baseline. Contact Platform Ops for any issues.'
});

CREATE (task_cleanup:MigrationTask {
  id: 'TASK-016',
  name: 'Source Project Deletion',
  category: 'cleanup',
  owner: 'app_team',
  is_automated: false,
  requires_service_request: true,
  service_request_type: 'incident',
  sequence_order: 16,
  description: 'After successful migration validation, delete project from source VMware cluster to free resources. Raise incident ticket for DEV or change ticket for UAT/PROD. Warning: Deleted projects cannot be restored.'
});


// ============================================================
// 9. NAMESPACES (Sample Applications)
// ============================================================

CREATE (ns_payments:Namespace {
  id: 'NS-001',
  name: 'payments-api',
  app_name: 'Payment Processing Service',
  app_id: 'APP-12345',
  env: 'DEV',
  sector: 'Finance',
  region: 'EAST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: true,
  uses_internal_systems: true
});

CREATE (ns_accounts:Namespace {
  id: 'NS-002',
  name: 'accounts-service',
  app_name: 'Account Management Service',
  app_id: 'APP-12346',
  env: 'DEV',
  sector: 'Finance',
  region: 'EAST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: false,
  uses_internal_systems: true
});

CREATE (ns_auth:Namespace {
  id: 'NS-003',
  name: 'auth-gateway',
  app_name: 'Authentication Gateway',
  app_id: 'APP-12347',
  env: 'DEV',
  sector: 'Security',
  region: 'EAST',
  network_type: 'dmz',
  migration_status: 'in_progress',
  has_vanity_url: true,
  uses_internal_systems: false
});

CREATE (ns_reports:Namespace {
  id: 'NS-004',
  name: 'reporting-engine',
  app_name: 'Business Intelligence Reports',
  app_id: 'APP-12348',
  env: 'DEV',
  sector: 'Analytics',
  region: 'WEST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: false,
  uses_internal_systems: true
});

CREATE (ns_notifications:Namespace {
  id: 'NS-005',
  name: 'notification-service',
  app_name: 'Customer Notification Service',
  app_id: 'APP-12349',
  env: 'DEV',
  sector: 'Customer',
  region: 'EAST',
  network_type: 'internal',
  migration_status: 'completed',
  has_vanity_url: true,
  uses_internal_systems: false
});

CREATE (ns_trading:Namespace {
  id: 'NS-006',
  name: 'trading-platform',
  app_name: 'Securities Trading Platform',
  app_id: 'APP-12350',
  env: 'DEV',
  sector: 'Trading',
  region: 'EAST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: true,
  uses_internal_systems: true
});

CREATE (ns_risk:Namespace {
  id: 'NS-007',
  name: 'risk-calculator',
  app_name: 'Risk Assessment Engine',
  app_id: 'APP-12351',
  env: 'DEV',
  sector: 'Risk',
  region: 'WEST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: false,
  uses_internal_systems: true
});

CREATE (ns_kyc:Namespace {
  id: 'NS-008',
  name: 'kyc-service',
  app_name: 'Know Your Customer Service',
  app_id: 'APP-12352',
  env: 'DEV',
  sector: 'Compliance',
  region: 'EAST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: true,
  uses_internal_systems: true
});

CREATE (ns_loans:Namespace {
  id: 'NS-009',
  name: 'loan-origination',
  app_name: 'Loan Origination System',
  app_id: 'APP-12353',
  env: 'DEV',
  sector: 'Lending',
  region: 'WEST',
  network_type: 'internal',
  migration_status: 'pending',
  has_vanity_url: false,
  uses_internal_systems: true
});

CREATE (ns_mobile:Namespace {
  id: 'NS-010',
  name: 'mobile-backend',
  app_name: 'Mobile Banking Backend',
  app_id: 'APP-12354',
  env: 'DEV',
  sector: 'Digital',
  region: 'EAST',
  network_type: 'dmz',
  migration_status: 'pending',
  has_vanity_url: true,
  uses_internal_systems: false
});


// ============================================================
// 10. RELATIONSHIPS
// ============================================================

// --- Cluster configurations ---
MATCH (c:DestinationCluster {id: 'BAREMETAL-EAST-DEV'}), (cfg:ClusterConfig {id: 'CFG-BAREMETAL-EAST-DEV'})
CREATE (c)-[:HAS_CONFIG]->(cfg);

MATCH (c:DestinationCluster {id: 'BAREMETAL-EAST-UAT'}), (cfg:ClusterConfig {id: 'CFG-BAREMETAL-EAST-UAT'})
CREATE (c)-[:HAS_CONFIG]->(cfg);

MATCH (c:DestinationCluster {id: 'BAREMETAL-WEST-DEV'}), (cfg:ClusterConfig {id: 'CFG-BAREMETAL-WEST-DEV'})
CREATE (c)-[:HAS_CONFIG]->(cfg);

MATCH (c:DestinationCluster {id: 'BAREMETAL-WEST-UAT'}), (cfg:ClusterConfig {id: 'CFG-BAREMETAL-WEST-UAT'})
CREATE (c)-[:HAS_CONFIG]->(cfg);

// --- Source to destination cluster mappings ---
MATCH (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (src)-[:MAPS_TO]->(dest);

MATCH (src:SourceCluster {id: 'VMWARE-EAST-UAT-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-UAT'})
CREATE (src)-[:MAPS_TO]->(dest);

MATCH (src:SourceCluster {id: 'VMWARE-WEST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-WEST-DEV'})
CREATE (src)-[:MAPS_TO]->(dest);

MATCH (src:SourceCluster {id: 'VMWARE-WEST-UAT-1'}), (dest:DestinationCluster {id: 'BAREMETAL-WEST-UAT'})
CREATE (src)-[:MAPS_TO]->(dest);

// --- Storage class relationships ---
MATCH (src:SourceCluster), (sc:StorageClass {platform: 'source'})
CREATE (src)-[:HAS_STORAGE_CLASS]->(sc);

MATCH (dest:DestinationCluster), (sc:StorageClass {platform: 'destination'})
CREATE (dest)-[:HAS_STORAGE_CLASS]->(sc);

// --- Namespace migrations (EAST region) ---
MATCH (ns:Namespace {id: 'NS-001'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-002'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-003'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-005'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-006'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-008'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-010'}), (src:SourceCluster {id: 'VMWARE-EAST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-EAST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

// --- Namespace migrations (WEST region) ---
MATCH (ns:Namespace {id: 'NS-004'}), (src:SourceCluster {id: 'VMWARE-WEST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-WEST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-007'}), (src:SourceCluster {id: 'VMWARE-WEST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-WEST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

MATCH (ns:Namespace {id: 'NS-009'}), (src:SourceCluster {id: 'VMWARE-WEST-DEV-1'}), (dest:DestinationCluster {id: 'BAREMETAL-WEST-DEV'})
CREATE (ns)-[:MIGRATES_FROM]->(src), (ns)-[:MIGRATES_TO]->(dest);

// --- Namespace egress IPs (EAST) ---
MATCH (ns:Namespace {id: 'NS-001'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-EAST-DEV-1'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-EAST-DEV-1'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

MATCH (ns:Namespace {id: 'NS-002'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-EAST-DEV-2'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-EAST-DEV-2'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

MATCH (ns:Namespace {id: 'NS-003'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-EAST-DEV-1'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-EAST-DEV-1'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

MATCH (ns:Namespace {id: 'NS-006'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-EAST-DEV-2'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-EAST-DEV-2'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

// --- Namespace egress IPs (WEST) ---
MATCH (ns:Namespace {id: 'NS-004'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-WEST-DEV-1'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-WEST-DEV-1'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

MATCH (ns:Namespace {id: 'NS-007'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-WEST-DEV-2'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-WEST-DEV-2'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

MATCH (ns:Namespace {id: 'NS-009'}), (src_ip:EgressIP {id: 'EGRESS-VMWARE-WEST-DEV-1'}), (dest_ip:EgressIP {id: 'EGRESS-BAREMETAL-WEST-DEV-1'})
CREATE (ns)-[:HAS_SOURCE_EGRESS]->(src_ip), (ns)-[:HAS_DEST_EGRESS]->(dest_ip);

// --- Namespace to phase ---
MATCH (ns:Namespace {env: 'DEV'}), (phase:MigrationPhase {name: 'DEV'})
CREATE (ns)-[:SCHEDULED_IN]->(phase);

// --- Namespace to CD tool ---
MATCH (ns:Namespace {id: 'NS-001'}), (cd:CDToolType {id: 'CD-TOOL-A'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-002'}), (cd:CDToolType {id: 'CD-TOOL-B'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-003'}), (cd:CDToolType {id: 'CD-TOOL-A'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-004'}), (cd:CDToolType {id: 'CD-TOOL-C'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-005'}), (cd:CDToolType {id: 'CD-TOOL-A'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-006'}), (cd:CDToolType {id: 'CD-TOOL-B'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-007'}), (cd:CDToolType {id: 'CD-TOOL-A'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-008'}), (cd:CDToolType {id: 'CD-TOOL-C'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-009'}), (cd:CDToolType {id: 'CD-TOOL-B'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

MATCH (ns:Namespace {id: 'NS-010'}), (cd:CDToolType {id: 'CD-TOOL-A'})
CREATE (ns)-[:USES_CD_TOOL]->(cd);

// --- Task prerequisites ---
// Firewall must be done before deployment
MATCH (t1:MigrationTask {id: 'TASK-004'}), (t2:MigrationTask {id: 'TASK-013'})
CREATE (t1)-[:PREREQUISITE_FOR]->(t2);

// Certificates before deployment
MATCH (t1:MigrationTask {id: 'TASK-006'}), (t2:MigrationTask {id: 'TASK-013'})
CREATE (t1)-[:PREREQUISITE_FOR]->(t2);

// SSO before deployment
MATCH (t1:MigrationTask {id: 'TASK-008'}), (t2:MigrationTask {id: 'TASK-013'})
CREATE (t1)-[:PREREQUISITE_FOR]->(t2);

// CD update before deployment
MATCH (t1:MigrationTask {id: 'TASK-012'}), (t2:MigrationTask {id: 'TASK-013'})
CREATE (t1)-[:PREREQUISITE_FOR]->(t2);

// Deployment before validation
MATCH (t1:MigrationTask {id: 'TASK-013'}), (t2:MigrationTask {id: 'TASK-015'})
CREATE (t1)-[:PREREQUISITE_FOR]->(t2);

// Validation before cleanup
MATCH (t1:MigrationTask {id: 'TASK-015'}), (t2:MigrationTask {id: 'TASK-016'})
CREATE (t1)-[:PREREQUISITE_FOR]->(t2);

// --- CD tool specific tasks ---
MATCH (t:MigrationTask {id: 'TASK-012'}), (cd:CDToolType)
CREATE (t)-[:SPECIFIC_TO_CD_TOOL]->(cd);


// ============================================================
// 11. SUMMARY
// ============================================================

RETURN 'VMware to BareMetal OpenShift Migration Knowledge Graph Loaded' as status;
