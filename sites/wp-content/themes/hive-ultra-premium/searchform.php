<?php
/**
 * Search form template
 *
 * @package Hive_Ultra_Premium
 */
?>
<form role="search" method="get" class="search-form" action="<?php echo esc_url(home_url('/')); ?>">
    <label class="screen-reader-text" for="hive-search"><?php esc_html_e('Ara', 'hive-ultra-premium'); ?></label>
    <input type="search" id="hive-search" name="s" value="<?php echo esc_attr(get_search_query()); ?>" placeholder="<?php esc_attr_e('İlan adı, kullanıcı adı, kategori, lokasyon ara…', 'hive-ultra-premium'); ?>" />
    <input type="hidden" name="post_type" value="companion_profile" />
    <button type="submit" class="btn btn-primary btn-small"><?php esc_html_e('Ara', 'hive-ultra-premium'); ?></button>
</form>
