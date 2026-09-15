# Lima ARM64 KVM validation

Use this procedure when the user selects a local Apple Silicon VM for a hardware-virtualized runtime. A single runtime preflight VM is a valid explicit scope; it does not establish a three-node ADX deployment.

## Discover before provisioning

Look up the caller's recorded `LIMA_HOME` and tool directory, not only `command -v limactl` or `~/.lima`. Previous local deployments may keep Lima in a project tool cache and VMs under a custom home. Record the resolved executable and run `limactl --version` plus `LIMA_HOME=... limactl list`. Reuse an installed compatible version. Do not start, edit or clone unrelated VMs merely because they are stopped.

On macOS query the actual host capability:

```sh
xcrun swift -e 'import Virtualization; if #available(macOS 15.0, *) { print(VZGenericPlatformConfiguration.isNestedVirtualizationSupported) }'
```

An ARM Mac alone is insufficient. A true host capability result does not prove the existing Docker Desktop Linux VM exports KVM. Check the selected guest itself.

## Isolated VM

Use a short dedicated `LIMA_HOME`, a caller-selected name and a digest-pinned Linux ARM64 cloud image from the installed Lima template. Essential settings:

```yaml
vmType: vz
arch: aarch64
nestedVirtualization: true
cpus: 4
memory: 6GiB
disk: 40GiB
mounts: []
containerd:
  system: false
  user: false
```

Add the resolved `images` entry; this fragment alone is not a pinned boot configuration. Start with `limactl start --tty=false --name=NAME CONFIG`. Avoid silent fallback to a mutable image if the pinned URL has expired; resolve and record a new digest. Use the existing proxy only where necessary for downloads. Preserve external proxy routing while bypassing proxies for actual service addresses.

After boot, record Linux architecture/kernel, machine ID, addresses, filesystem type, cgroup controllers and free disk. From this skill directory, run the KVM helper in the guest with permissions equivalent to the backend (or use its resolved absolute path):

```sh
limactl shell NAME -- sudo python3 - < scripts/kvm_probe.py
```

Pass requires KVM API version 12 and successful `KVM_CREATE_VM` plus `KVM_CREATE_VCPU`; merely finding `/dev/kvm` is not a pass. The helper closes all FDs and leaves no VM process. This still does not exercise a guest boot or snapshot restore.

Keep sandboxd filestore, writable images and checkpoint files on the guest's native Linux disk. Transfer artifacts with `limactl copy` or tar over `limactl shell`; macOS shared directories are suitable for transfer, not the runtime's nested mount tree. Enable the selected runtime's forwarding, TAP, loop-device and writable cgroup prerequisites in this dedicated guest. With sandboxd network ACL enabled, install `ipset` in addition to `iptables`, load `br_netfilter` and verify `net.bridge.bridge-nf-call-iptables=1`; a missing `/proc/sys/net/bridge` blocks sandboxd initialization. For its local DNAT path also verify `net.ipv4.conf.all.rp_filter=0`. Persist the required modules and sysctls for a reusable VM and verify them after reboot.

## Runtime acceptance

For the selected sandboxd Firecracker restore path, enable its node-resource provider so restore can reserve memory. In a standalone VM the backend's existing E2E uses:

```toml
[plugin.node_resource]
provider = "cgroup"
sock_path = "/run/sandboxd/resource.sock"
```

This is real resource observation; do not replace it with invented capacity. Missing this configuration can allow start/checkpoint while rejecting restore with `Firecracker checkpoint requires node memory reservation`.

Before claiming Firecracker readiness, follow the pinned sandboxd backend contract and test actual start → exec/file write → checkpoint with source stopped → restore → exec/file read → delete. A successful Restore RPC is insufficient: verify that the restored process stays running, preserves in-memory progress, and does not rerun its entrypoint. For the matching sandboxd checkout, inspect `test/e2e/checkpoint-restore/main.go` and the Firecracker configuration in `test/e2e/e2e-run.sh`. The helper exposes `--action start|checkpoint|restore|delete`, `--request-file`, `--checkpoint-dir` and `--leave-running=false`; compile it from that same revision. Use a unique checkpoint directory per run and test-owned IDs. Keep the rootfs immutable for the lifetime of any retained checkpoint. Save individual verdicts and both sandboxd and guest/VMM logs. Record final instance inventory and preserve the VM for reuse unless the user requested teardown. For a newly provisioned reusable VM, verify module/sysctl/KVM readiness and a runtime smoke after a VM stop/start; keep the inventory and exact rerun commands outside this toolkit.

Use the selected ADX checkout's runtime pin; an x86_64-only release must not run through emulation to establish ARM64 acceptance. Build the same fork/tag outside the runtime VM, including an ARM64 guest kernel and a matching static sandboxd guest agent in the initrd. Prefer the supported `aarch64-unknown-linux-musl` VMM target: the GNU target can fall back to an empty default seccomp policy. Inspect build warnings and hashes instead of relying on the image tag or `--version` alone. For ARM64 the Firecracker boot artifact is the kernel `Image`, not an x86_64 ELF `vmlinux`; merge the fork's required filesystem/network configuration into its ARM64 base config.

Sources: [Lima nested virtualization configuration](https://github.com/lima-vm/lima/blob/master/templates/default.yaml), [Firecracker setup](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md). Recheck the installed version's actual contract.

## Native ARM64 builder details

For a native Debian/Ubuntu builder using `musl-tools`, make the selected musl compiler explicit. The fork's build-time seccompiler needs `libseccomp-dev`. If userfaultfd's C build cannot find `linux/types.h`, provide Linux UAPI headers after the musl headers rather than replacing the libc include tree:

```sh
export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=musl-gcc
export CC_aarch64_unknown_linux_musl=musl-gcc
export CFLAGS_aarch64_unknown_linux_musl="-idirafter /usr/include -idirafter /usr/include/aarch64-linux-gnu"
```

These paths describe the Debian multiarch layout; verify the builder before using them. Persist Cargo registry/git/target caches separately from output artifacts. Use the checkout's toolchain and lockfile, configured registry source, bounded build parallelism, and saved logs. Verify the generated target-specific seccomp filter, static ELF architecture, kernel config, guest agent revision and artifact hashes before copying to the VM.
