# ADX Toolkit maintenance

- Maintain exactly the four named skills unless the user requests another.
- Keep each skill self-contained; references and helpers live below its own directory.
- Derive operational commands from the selected ADX checkout. Avoid embedding host inventory, credentials, local absolute paths, mutable branch results or unverified deployment claims.
- Keep product code and execution evidence outside this repository. Do not copy product build systems into a skill.
- Validate skill metadata, links and helper behavior. Use narrow-context subagents for long builds, tests or CI monitoring; provide repository, exact command, concurrency, success criteria and log path. Workers do not edit source and poll every 60–180 seconds.
- Use conventional commit subjects with one Signed-off-by trailer. Never publish credentials or enlarge repository visibility without authorization.
