# Local LLM Notes

## Hardware

Idea here is how do you take an old desktop w/ a decent GPU and use it to self-host an LLM for local network access.

- Mine has a 2070 Super with 8GB VRAM — good for 7B models with quantization and decent prototyping

### What Runs on 8GB VRAM

VRAM is the limiting factor. Model must fit in VRAM to run at usable speed.

- 7B parameter models — run well at full or Q4 quantization (Llama 3, Mistral 7B, Qwen 2.5 7B)
- 8B models — fit with Q4 quantization
- 13B+ models — too large, offload to RAM and become slow

Quantization compresses a model to fit in less VRAM with minimal quality loss. Q4 is the standard tradeoff for 8GB cards.

---

## Approach 1: Run Ollama on the Host (Recommended)

Ollama runs directly on the Linux desktop as a native process. No k3s involvement.

### Setup

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
ollama serve
```

Exposes a REST API at `http://<desktop-ip>:11434` on your local network. Any device or pod on the same network can call it by IP.

For a clean local hostname instead of an IP, set a DNS entry in Pi-hole or your router pointing `llm.home` at the desktop's static IP.

Assign a static IP either via static network config on the desktop or via a DHCP reservation in your router (preferred — keeps network config centralized).

### Pros

- Simple setup, done in an afternoon
- No driver/container compatibility issues
- No cluster maintenance overhead
- Functionally identical result — a URL your cluster can call

### Cons

- Not managed by k3s — separate thing to monitor and maintain
- No cluster-native service discovery or ingress
- Have to manage Ollama as a systemd service or similar on the host

---

## Approach 2: Desktop as a K3s Node with GPU Passthrough

Add the desktop as a fourth node in the cluster. Run Ollama as a k3s deployment with GPU access. Expose via Traefik at a cluster-managed hostname.

### Setup Requirements

Install NVIDIA container toolkit on the node:

```bash
# adds nvidia runtime support to containerd
apt install nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=containerd
systemctl restart containerd
```

- This makes the GPU available as a resource that can be allocated to containers. The NVIDIA device plugin then exposes that resource to the cluster for scheduling.

Deploy the NVIDIA device plugin as a DaemonSet:

```yaml
releases:
  - name: nvidia-device-plugin
    namespace: kube-system
    chart: nvdp/nvidia-device-plugin
    version: 0.17.0
    values:
      - nodeSelector:
          gpu: "true"
```

- The selector ensures the plugin only runs on the GPU nodes, because it'd be useless to have this run on nodes without GPUs.

Label the node:

```bash
kubectl label node <desktop-node> gpu=true
```

Now you'd have the node tagged w/ `gpu=true`, so the Nvidia Device Plugin would run on it as a DaemonSet, and the GPU resource would be available for scheduling.

Ollama deployment spec:

```yaml
spec:
  template:
    spec:
      nodeSelector:
        gpu: "true"
      containers:
        - name: ollama
          image: ollama/ollama
          resources:
            limits:
              nvidia.com/gpu: 1
```

The `nvidia.com/gpu` resource limit is what gates GPU access. The NVIDIA device plugin makes that resource available on the node. The node label ensures the pod schedules on the right machine — same pattern as the Zigbee and Z-Wave coordinator pods.

Then expose via a Traefik IngressRoute:

```yaml
apiVersion: traefik.io/v1alpha1
kind: IngressRoute
metadata:
  name: ollama
spec:
  entryPoints:
    - web
  routes:
    - match: Host(`llm.home`)
      kind: Rule
      services:
        - name: ollama
          port: 11434
```

### Pros

- Fully cluster-managed — same deployment, monitoring, and ingress patterns as everything else
- Clean hostname via Traefik (`http://llm.home/v1/api`)
- Node labeling pattern is consistent with USB dongle nodes

### Cons

- NVIDIA container toolkit is tightly coupled to kernel version — breaks on kernel or driver updates
- Real maintenance overhead in a homelab context
- Adds a fourth node with different hardware characteristics to manage
- Significant setup complexity for a result that is functionally the same as approach 1

---

## Recommendation

Run Ollama on the host. Set a static IP or local DNS entry. The end result is identical — a local endpoint your cluster and HA can call — without the GPU passthrough complexity.

Revisit the cluster node approach if you later have workloads that benefit from GPU access beyond just the LLM (e.g. Frigate with a dedicated GPU for object detection).

---

## Home Assistant Integration

HA has a native Ollama integration. Point it at your desktop's IP and it uses the local LLM for:

- Conversational assistant inside HA
- Natural language automation triggers
- Local voice assistant (no cloud)

Config in HA just requires the host URL and model name. No API key needed for a local Ollama instance.
