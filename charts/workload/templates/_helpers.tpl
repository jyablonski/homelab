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

{{- define "workload.jobName" -}}
{{- printf "%s-%s" (include "workload.fullname" .root) .jobName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "workload.jobLabels" -}}
homelab.jacob/runnable: {{ default false .job.runnable | quote }}
homelab.jacob/app: {{ include "workload.fullname" .root | quote }}
homelab.jacob/job: {{ .jobName | quote }}
{{- end -}}

{{- define "workload.imageRepository" -}}
{{- if .Values.image.repository -}}
{{- .Values.image.repository -}}
{{- else -}}
{{- printf "%s/%s/%s" (default "registry.home:5000" .Values.image.registry) (default "homelab" .Values.image.project) .Release.Name -}}
{{- end -}}
{{- end -}}

{{- define "workload.image" -}}
{{- printf "%s:%s" (include "workload.imageRepository" .) .Values.image.tag -}}
{{- end -}}

{{- define "workload.imagePullPolicy" -}}
{{- .Values.image.pullPolicy -}}
{{- end -}}

{{- define "workload.replicas" -}}
{{- if .Values.scale -}}
{{- .Values.scale.replicas | default 1 -}}
{{- else -}}
{{- .Values.replicaCount | default 1 -}}
{{- end -}}
{{- end -}}

{{- define "workload.containerPort" -}}
{{- if .Values.service.targetPort -}}
{{- .Values.service.targetPort -}}
{{- else if .Values.service.port -}}
{{- .Values.service.port -}}
{{- else -}}
{{- .Values.containerPort -}}
{{- end -}}
{{- end -}}

{{- define "workload.podLabels" -}}
{{- $labels := dict "app.kubernetes.io/component" (include "workload.name" .) -}}
{{- merge $labels .Values.podLabels | toYaml -}}
{{- end -}}
