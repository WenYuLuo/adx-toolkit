#!/usr/bin/env python3
"""Check KVM API and VM/vCPU creation on the selected Linux host; leave no running VM."""
import fcntl, json, os, platform
result = {"architecture": platform.machine(), "kernel": platform.release()}
fds = []
try:
    kvm = os.open("/dev/kvm", os.O_RDWR | os.O_CLOEXEC); fds.append(kvm)
    result["api_version"] = fcntl.ioctl(kvm, 0xAE00, 0)
    assert result["api_version"] == 12
    vm = fcntl.ioctl(kvm, 0xAE01, 0); fds.append(vm)
    vcpu = fcntl.ioctl(vm, 0xAE41, 0); fds.append(vcpu)
    result.update(create_vm=True, create_vcpu=True, passed=True)
except BaseException as exc:
    result.update(passed=False, error=repr(exc))
    raise
finally:
    for fd in reversed(fds): os.close(fd)
    print(json.dumps(result, indent=2))
