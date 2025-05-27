# KRR CRD-Based Reports Design Document

## Executive Summary

This document outlines the design for implementing Custom Resource Definitions (CRDs) to store and manage KRR (Kubernetes Resource Recommender) recommendations as native Kubernetes resources. This approach enables GitOps workflows, audit trails, and automated recommendation management.

## Goals

1. **Enable GitOps**: Store recommendations as versionable, declarative resources
2. **Provide Audit Trail**: Track all recommendations, approvals, and applications
3. **Support Automation**: Allow controllers to act on recommendations
4. **Maintain Flexibility**: Support various approval and rollout strategies
5. **Enable Integration**: Work with existing Kubernetes tooling and workflows

## CRD Specifications

### 1. ResourceRecommendation CRD

The primary CRD for storing individual workload recommendations.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: resourcerecommendations.krr.robusta.dev
spec:
  group: krr.robusta.dev
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required: ["spec"]
        properties:
          spec:
            type: object
            required: ["targetRef", "recommendations", "analysis"]
            properties:
              targetRef:
                type: object
                required: ["kind", "name"]
                properties:
                  apiVersion:
                    type: string
                    default: "apps/v1"
                  kind:
                    type: string
                    enum: ["Deployment", "StatefulSet", "DaemonSet", "Job", "Rollout"]
                  name:
                    type: string
                  namespace:
                    type: string
              
              recommendations:
                type: object
                properties:
                  containers:
                    type: array
                    items:
                      type: object
                      required: ["name", "resources"]
                      properties:
                        name:
                          type: string
                        resources:
                          type: object
                          properties:
                            cpu:
                              type: object
                              properties:
                                request:
                                  type: string
                                  pattern: "^[0-9]+(\\.[0-9]+)?(m|)$"
                                limit:
                                  type: string
                                  pattern: "^[0-9]+(\\.[0-9]+)?(m|)$"
                            memory:
                              type: object
                              properties:
                                request:
                                  type: string
                                  pattern: "^[0-9]+(\\.[0-9]+)?(Mi|Gi|Ki|M|G|K)$"
                                limit:
                                  type: string
                                  pattern: "^[0-9]+(\\.[0-9]+)?(Mi|Gi|Ki|M|G|K)$"
              
              analysis:
                type: object
                required: ["strategy", "dataPoints", "confidence"]
                properties:
                  strategy:
                    type: string
                    enum: ["simple", "simple-limit", "ml-based", "custom"]
                  historyDuration:
                    type: string
                    pattern: "^[0-9]+(h|d|w)$"
                  dataPoints:
                    type: integer
                    minimum: 1
                  confidence:
                    type: number
                    minimum: 0
                    maximum: 1
                  metrics:
                    type: object
                    properties:
                      cpu:
                        type: object
                        properties:
                          p50:
                            type: string
                          p95:
                            type: string
                          p99:
                            type: string
                          max:
                            type: string
                      memory:
                        type: object
                        properties:
                          p50:
                            type: string
                          p95:
                            type: string
                          p99:
                            type: string
                          max:
                            type: string
              
              impact:
                type: object
                properties:
                  estimatedSavings:
                    type: object
                    properties:
                      cpu:
                        type: string
                      memory:
                        type: string
                      monthlyCost:
                        type: string
                  severity:
                    type: string
                    enum: ["critical", "warning", "info"]
                  
          status:
            type: object
            properties:
              phase:
                type: string
                enum: ["pending", "approved", "applied", "failed", "rejected"]
              conditions:
                type: array
                items:
                  type: object
                  properties:
                    type:
                      type: string
                    status:
                      type: string
                    lastTransitionTime:
                      type: string
                    reason:
                      type: string
                    message:
                      type: string
              appliedAt:
                type: string
              appliedBy:
                type: string
              actualSavings:
                type: object
                properties:
                  cpu:
                    type: string
                  memory:
                    type: string
                  monthlyCost:
                    type: string
    additionalPrinterColumns:
    - name: Target
      type: string
      jsonPath: .spec.targetRef.name
    - name: Kind
      type: string
      jsonPath: .spec.targetRef.kind
    - name: Strategy
      type: string
      jsonPath: .spec.analysis.strategy
    - name: Confidence
      type: number
      jsonPath: .spec.analysis.confidence
    - name: Phase
      type: string
      jsonPath: .status.phase
    - name: Age
      type: date
      jsonPath: .metadata.creationTimestamp
```

### 2. RecommendationReport CRD

Aggregates multiple recommendations into a report.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: recommendationreports.krr.robusta.dev
spec:
  group: krr.robusta.dev
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required: ["spec"]
        properties:
          spec:
            type: object
            required: ["scanTime", "scope"]
            properties:
              scanTime:
                type: string
                format: date-time
              scope:
                type: object
                properties:
                  clusters:
                    type: array
                    items:
                      type: string
                  namespaces:
                    type: array
                    items:
                      type: string
                  labelSelector:
                    type: string
              
              summary:
                type: object
                properties:
                  totalWorkloads:
                    type: integer
                  totalRecommendations:
                    type: integer
                  estimatedMonthlySavings:
                    type: string
                  byNamespace:
                    type: object
                    additionalProperties:
                      type: object
                      properties:
                        workloads:
                          type: integer
                        savings:
                          type: string
                  bySeverity:
                    type: object
                    properties:
                      critical:
                        type: integer
                      warning:
                        type: integer
                      info:
                        type: integer
              
              recommendations:
                type: array
                items:
                  type: object
                  properties:
                    name:
                      type: string
                    namespace:
                      type: string
          
          status:
            type: object
            properties:
              phase:
                type: string
                enum: ["completed", "partial", "failed"]
              completionTime:
                type: string
              recommendationsCreated:
                type: integer
              errors:
                type: array
                items:
                  type: string
```

### 3. RecommendationPolicy CRD

Defines policies for automated recommendation application.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: recommendationpolicies.krr.robusta.dev
spec:
  group: krr.robusta.dev
  scope: Cluster
  versions:
  - name: v1alpha1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        required: ["spec"]
        properties:
          spec:
            type: object
            properties:
              selector:
                type: object
                properties:
                  namespaces:
                    type: array
                    items:
                      type: string
                  workloadSelector:
                    type: object
                    properties:
                      matchLabels:
                        type: object
                        additionalProperties:
                          type: string
              
              autoApply:
                type: object
                properties:
                  enabled:
                    type: boolean
                    default: false
                  requireApproval:
                    type: boolean
                    default: true
                  approvers:
                    type: array
                    items:
                      type: string
                  maxChangePercent:
                    type: integer
                    minimum: 0
                    maximum: 100
                    default: 20
              
              rolloutStrategy:
                type: object
                properties:
                  type:
                    type: string
                    enum: ["immediate", "canary", "bluegreen"]
                    default: "immediate"
                  canary:
                    type: object
                    properties:
                      steps:
                        type: array
                        items:
                          type: object
                          properties:
                            percentage:
                              type: integer
                            duration:
                              type: string
                      analysis:
                        type: object
                        properties:
                          metrics:
                            type: array
                            items:
                              type: string
                          failureThreshold:
                            type: integer
              
              validation:
                type: object
                properties:
                  minConfidence:
                    type: number
                    default: 0.8
                  minDataPoints:
                    type: integer
                    default: 100
                  requireSLO:
                    type: boolean
                    default: false
```

## Implementation Architecture

### Component Overview

```
┌─────────────────────┐
│   KRR CLI/Scanner   │
└──────────┬──────────┘
           │ Creates
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│ResourceRecommendation│────▶│RecommendationReport │
│        CRDs         │     │        CRD          │
└──────────┬──────────┘     └─────────────────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Recommendation     │────▶│RecommendationPolicy │
│    Controller       │     │        CRD          │
└──────────┬──────────┘     └─────────────────────┘
           │ Applies
           ▼
┌─────────────────────┐
│Workload (Deployment)│
└─────────────────────┘
```

### KRR CLI Extensions

New output formatter for CRDs:

```python
# robusta_krr/formatters/crd.py
class CRDFormatter(BaseFormatter):
    def format(self, recommendations: List[Recommendation]) -> List[Dict]:
        crds = []
        report_crd = self._create_report_crd(recommendations)
        crds.append(report_crd)
        
        for rec in recommendations:
            crd = self._create_recommendation_crd(rec)
            crds.append(crd)
        
        return crds
    
    def _create_recommendation_crd(self, rec: Recommendation) -> Dict:
        return {
            "apiVersion": "krr.robusta.dev/v1alpha1",
            "kind": "ResourceRecommendation",
            "metadata": {
                "name": f"{rec.workload_name}-{rec.timestamp}",
                "namespace": rec.namespace,
                "labels": {
                    "krr.robusta.dev/workload": rec.workload_name,
                    "krr.robusta.dev/type": rec.workload_type,
                    "krr.robusta.dev/scan-id": rec.scan_id
                }
            },
            "spec": {
                "targetRef": {
                    "kind": rec.workload_type,
                    "name": rec.workload_name,
                    "namespace": rec.namespace
                },
                "recommendations": {
                    "containers": rec.container_recommendations
                },
                "analysis": {
                    "strategy": rec.strategy,
                    "historyDuration": rec.history_duration,
                    "dataPoints": rec.data_points,
                    "confidence": rec.confidence,
                    "metrics": rec.metrics_summary
                },
                "impact": {
                    "estimatedSavings": rec.estimated_savings,
                    "severity": rec.severity
                }
            }
        }
```

### Recommendation Controller

A Kubernetes controller that watches and acts on ResourceRecommendation CRDs:

```go
// pkg/controller/recommendation_controller.go
type RecommendationController struct {
    client     client.Client
    scheme     *runtime.Scheme
    policyCtrl *PolicyController
}

func (r *RecommendationController) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    // 1. Fetch the ResourceRecommendation
    recommendation := &krrv1alpha1.ResourceRecommendation{}
    if err := r.client.Get(ctx, req.NamespacedName, recommendation); err != nil {
        return ctrl.Result{}, err
    }
    
    // 2. Check if recommendation should be auto-applied
    policy, err := r.policyCtrl.GetPolicyFor(recommendation)
    if err != nil || !policy.Spec.AutoApply.Enabled {
        return ctrl.Result{}, nil
    }
    
    // 3. Validate recommendation meets policy requirements
    if !r.validateRecommendation(recommendation, policy) {
        return ctrl.Result{}, r.updateStatus(recommendation, "ValidationFailed")
    }
    
    // 4. Check for approval if required
    if policy.Spec.AutoApply.RequireApproval && !r.hasApproval(recommendation) {
        return ctrl.Result{RequeueAfter: time.Hour}, nil
    }
    
    // 5. Apply recommendation using rollout strategy
    if err := r.applyRecommendation(recommendation, policy); err != nil {
        return ctrl.Result{}, r.updateStatus(recommendation, "Failed", err.Error())
    }
    
    return ctrl.Result{}, r.updateStatus(recommendation, "Applied")
}
```

## Usage Workflows

### 1. GitOps Workflow

```bash
# Generate recommendations as CRDs
krr simple -f crd -o ./recommendations/

# Review and commit
git add recommendations/
git commit -m "KRR recommendations - $(date)"
git push

# ArgoCD/Flux syncs CRDs to cluster
# Controller optionally auto-applies based on policies
```

### 2. Manual Approval Workflow

```yaml
# Add approval annotation
kubectl annotate resourcerecommendation nginx-deployment-rec \
  krr.robusta.dev/approved-by="platform-team" \
  krr.robusta.dev/approved="true"

# Controller detects approval and applies
```

### 3. Progressive Rollout

```yaml
# Define canary rollout policy
apiVersion: krr.robusta.dev/v1alpha1
kind: RecommendationPolicy
metadata:
  name: production-canary
spec:
  selector:
    namespaces: ["production"]
  rolloutStrategy:
    type: canary
    canary:
      steps:
      - percentage: 10
        duration: "2h"
      - percentage: 50
        duration: "24h"
      - percentage: 100
```

## Integration Points

### 1. Monitoring Integration

```yaml
# Prometheus Rule for tracking savings
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: krr-savings
spec:
  groups:
  - name: krr
    rules:
    - alert: SignificantSavingsAvailable
      expr: |
        sum(krr_estimated_monthly_savings) by (namespace) > 1000
      annotations:
        summary: "Significant cost savings available in {{ $labels.namespace }}"
```

### 2. Webhook Notifications

```yaml
# ResourceRecommendation with webhook
metadata:
  annotations:
    krr.robusta.dev/notify-webhook: "https://slack.company.com/krr-hook"
    krr.robusta.dev/notify-on: "created,approved,applied"
```

### 3. RBAC Configuration

```yaml
# Role for viewing recommendations
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: krr-viewer
rules:
- apiGroups: ["krr.robusta.dev"]
  resources: ["resourcerecommendations", "recommendationreports"]
  verbs: ["get", "list", "watch"]

---
# Role for approving recommendations
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: krr-approver
rules:
- apiGroups: ["krr.robusta.dev"]
  resources: ["resourcerecommendations"]
  verbs: ["get", "list", "patch", "update"]
```

## Benefits

1. **Version Control**: All recommendations tracked in Git
2. **Audit Trail**: Complete history of what was recommended, approved, and applied
3. **Automation**: Controllers can act on recommendations based on policies
4. **Integration**: Works with existing K8s tooling (kubectl, ArgoCD, etc.)
5. **Flexibility**: Supports various approval and rollout strategies
6. **Observability**: Can be monitored like any other K8s resource

## Migration Path

### Phase 1: Read-Only CRDs
- Implement CRD formatter in KRR
- Generate CRDs alongside existing reports
- No controller, manual application only

### Phase 2: Basic Controller
- Implement controller for auto-application
- Support basic approval workflow
- Immediate rollout only

### Phase 3: Advanced Features
- Policy-based automation
- Progressive rollout strategies
- Full webhook integration
- Metrics and monitoring

## Open Questions

1. **Retention Policy**: How long to keep ResourceRecommendation CRDs?
2. **Multi-Cluster**: How to handle recommendations across clusters?
3. **Backwards Compatibility**: Support for non-CRD workflows?
4. **Performance**: Impact of many CRDs on etcd?

## Conclusion

The CRD-based approach transforms KRR from a scanning tool into a complete recommendation management system. It enables GitOps workflows, provides audit trails, and allows for sophisticated automation while maintaining the simplicity and flexibility that makes KRR valuable. 