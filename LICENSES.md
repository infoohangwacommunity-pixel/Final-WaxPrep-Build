# Licensing and Attribution Policy

## Project License

WaxPrep is released under the Apache License, Version 2.0.

The full license text is in the `LICENSE` file at the root of this repository.

Apache-2.0 is the license for original WaxPrep project code and documentation unless a file or component states otherwise.

## Third-Party Source Code Policy

WaxPrep may reuse existing open-source source code when the applicable license permits that reuse.

For copied source code, WaxPrep permits direct code reuse only from projects/files licensed under:

- MIT
- Apache License 2.0
- BSD-family permissive licenses, including BSD-2-Clause and BSD-3-Clause

The license must apply to the specific code being copied. A repository having an open-source license does not automatically mean that every file in the repository has the same licensing terms.

## Before Copying Code

Before copying any third-party source code into WaxPrep:

1. Identify the original source repository.
2. Identify the exact file or code location being copied.
3. Identify the commit from which the code is copied.
4. Verify the license that applies to that code.
5. Confirm that the license is one of the permitted licenses listed above.
6. Preserve required copyright, license, attribution, and other notices.
7. Record the copied code in `THIRD_PARTY`.

If the license is unclear, unavailable, incompatible, or outside the permitted list, do not copy the source code.

Architecture ideas, algorithms, design patterns, and publicly documented concepts may be studied and independently implemented, but source code must not be copied unless its license permits the reuse.

## Attribution Requirements

When third-party code is copied, all required copyright and license notices must be preserved.

Each copied source entry must be recorded in `THIRD_PARTY` with at least:

- source repository
- exact file
- source commit
- license
- description of what was reused
- where it is used in WaxPrep
- required attribution or notice information

If the original project provides additional attribution requirements, those requirements must also be followed.

## Dependencies

Dependencies are separate from WaxPrep's own project license.

A dependency may carry its own license even when WaxPrep itself is licensed under Apache-2.0.

Before a public release, the project's dependencies must be reviewed for:

- license compatibility
- required notices
- attribution requirements
- redistribution requirements
- other applicable license obligations

Dependency licenses must not be assumed to be Apache-2.0 simply because WaxPrep is Apache-2.0.

## No License Guessing

If the licensing status of source code cannot be established with reasonable confidence, treat the code as unavailable for direct copying.

Do not copy code first and investigate its license afterward.

## Record of Reused Code

`THIRD_PARTY` is the project's attribution ledger for copied third-party source code.

Every copied snippet must have a corresponding entry there.
