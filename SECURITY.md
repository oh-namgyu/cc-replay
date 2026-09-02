# Security

## What this tool does

cc-replay runs entirely on your machine. It reads a transcript file, writes an HTML file, and
makes no network requests — neither the CLI nor the generated page, which inlines all of its CSS,
JavaScript, data and favicon.

## Treat the output as sensitive

The generated HTML embeds your session: your prompts, the assistant's replies, and the full input
and output of every tool call. That can include file contents, command output and anything else
that passed through the session. **Treat a generated replay as being as sensitive as the session
it came from.**

## Redaction is best effort

Redaction is enabled by default and masks common secret shapes — API keys and tokens, `Bearer`
values, generic `key`/`token`/`secret`/`password` assignments, JWTs, private key blocks, email
addresses and home directory paths. The full list of categories is in the README.

It is **pattern-based and not a guarantee**. A credential in a shape the patterns do not cover will
pass through untouched. Always review a replay before sharing it.

Running with `--no-redact` disables masking entirely. Pages produced that way are marked with an
"⚠ unredacted" badge in the footer.

## Reporting a problem

Please report security issues — in particular any way transcript content can escape escaping in the
generated page, or a common secret shape that redaction misses — through GitHub issues on this
repository. Include the shape of the input rather than the real secret.
