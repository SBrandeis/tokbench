const NAME: &str = "pipeline-base";
const NO_CACHE_NAME: &str = "pipeline-base-no-cache";
const VERSION: &str = "tokenizers @ 76f57f25";
const URL: &str =
    "https://github.com/huggingface/tokenizers/tree/76f57f25a39f139d92ae861db950b7830951e6d2";

#[path = "../../pipeline/src/adapter.rs"]
mod adapter;
pub use adapter::Adapter;
