{{/*
Return the namespace for the cronjob resources.
If namespaceOverride is set in values, use it.
Otherwise default to "cronjob".
*/}}
{{- define "cronjob.namespace" -}}
{{- if .namespaceOverride -}}
{{ .namespaceOverride }}
{{- else -}}
cronjob
{{- end -}}
{{- end -}}