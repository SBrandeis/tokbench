const NAME: &str = "pipeline";
const NO_CACHE_NAME: &str = "pipeline-no-cache";
const VERSION: &str = "tokenizers @ 76f57f25";
const URL: &str =
    "https://github.com/huggingface/tokenizers/tree/76f57f25a39f139d92ae861db950b7830951e6d2";

mod adapter;
pub use adapter::Adapter;
