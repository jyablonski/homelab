{{- define "workload.name" -}}
{{- default .Release.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "workload.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "workload.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "workload.selectorLabels" -}}
app.kubernetes.io/name: {{ include "workload.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "workload.labels" -}}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
helm.sh/chart: {{ include "workload.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{ include "workload.selectorLabels" . }}
{{- end -}}

{{- define "workload.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "workload.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "workload.traefikStripPrefixMiddlewareName" -}}
{{- printf "%s-strip-prefix" (include "workload.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "workload.traefikStripPrefixMiddlewareRef" -}}
{{- printf "%s-%s@kubernetescrd" .Release.Namespace (include "workload.traefikStripPrefixMiddlewareName" .) -}}
{{- end -}}
