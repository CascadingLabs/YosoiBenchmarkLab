use super::{Selector, TARGET_SELECTOR, digest_values, stream_values};

#[test]
fn streams_exact_values_across_arbitrary_chunk_boundaries() {
    let selector: Selector = TARGET_SELECTOR.parse().expect("frozen selector parses");
    let data = br#"<main><article class="product-card" data-selected="true"><span class="price"> USD <b>19.73</b> </span></article><article class="product-card"><span class="price">USD 1.00</span></article></main>"#;
    let expected = vec!["USD 19.73".to_owned()];
    for chunk_size in [1, 3, 7, 31, 256] {
        let values = stream_values(data, chunk_size, &selector).expect("streaming fixture parses");
        assert_eq!(values, expected, "chunk size {chunk_size}");
        assert_eq!(
            digest_values(&values).expect("values serialize"),
            digest_values(&expected).expect("oracle serializes")
        );
    }
}
