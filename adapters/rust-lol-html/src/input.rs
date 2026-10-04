use std::{fs::File, io::Read, path::Path};

use anyhow::{Context, Result, bail};

pub(super) fn read_bounded(path: &Path, maximum: usize) -> Result<Vec<u8>> {
    let read_limit = maximum.checked_add(1).context("input limit overflow")?;
    let read_limit = u64::try_from(read_limit).context("input limit does not fit u64")?;
    let file = File::open(path).with_context(|| format!("failed to open {}", path.display()))?;
    let mut bytes = Vec::new();
    file.take(read_limit)
        .read_to_end(&mut bytes)
        .with_context(|| format!("failed to read {}", path.display()))?;
    if bytes.len() > maximum {
        bail!("{} exceeds the {maximum}-byte limit", path.display());
    }
    Ok(bytes)
}
