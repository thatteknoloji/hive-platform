<?php
/**
 * Footer — yasal bağlantılar
 *
 * @package Hive_Ultra_Premium
 */
?>
<div class="footer-disclaimer">
    <p><small>&copy; <?php echo esc_html(date('Y')); ?> Bal Kutusu — <?php esc_html_e('HIVE Premium | Tüm hakları saklıdır.', 'hive-ultra-premium'); ?></small></p>
    <p class="footer-disclaimer-links">
        <small>
            <a href="<?php echo esc_url(hive_legal_page_url('sorumluluk-reddi')); ?>"><?php esc_html_e('Sorumluluk Reddi', 'hive-ultra-premium'); ?></a>
            <span aria-hidden="true"> | </span>
            <a href="<?php echo esc_url(hive_legal_page_url('gizlilik-politikasi')); ?>"><?php esc_html_e('Gizlilik Politikası', 'hive-ultra-premium'); ?></a>
            <span aria-hidden="true"> | </span>
            <a href="<?php echo esc_url(hive_legal_page_url('kullanim-sartlari')); ?>"><?php esc_html_e('Kullanım Şartları', 'hive-ultra-premium'); ?></a>
        </small>
    </p>
</div>
