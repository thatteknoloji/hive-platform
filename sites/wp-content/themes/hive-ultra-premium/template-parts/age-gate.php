<?php
/**
 * 18+ yaş doğrulama modalı
 *
 * @package Hive_Ultra_Premium
 */
?>
<div id="hive-age-gate" class="hive-age-gate" role="dialog" aria-modal="true" aria-labelledby="hive-age-gate-title" hidden>
    <div class="hive-age-gate-backdrop" aria-hidden="true"></div>
    <div class="hive-age-gate-card">
        <div class="hive-age-gate-badge" aria-hidden="true">18+</div>
        <h2 id="hive-age-gate-title" class="hive-age-gate-title"><?php esc_html_e('Yaş Doğrulama', 'hive-ultra-premium'); ?></h2>
        <p class="hive-age-gate-heading"><?php esc_html_e('Bu site yalnızca 18 yaş ve üzeri yetişkinler içindir.', 'hive-ultra-premium'); ?></p>
        <p class="hive-age-gate-text"><?php esc_html_e('Devam etmek için 18 yaşından büyük olduğunuzu onaylamanız gerekmektedir. Site içeriği yetişkinlere yöneliktir.', 'hive-ultra-premium'); ?></p>
        <div class="hive-age-gate-actions">
            <button type="button" class="btn btn-primary hive-age-gate-confirm" id="hive-age-confirm">
                <?php esc_html_e('Evet, 18 yaşından büyüğüm', 'hive-ultra-premium'); ?>
            </button>
            <button type="button" class="btn hive-age-gate-deny" id="hive-age-deny">
                <?php esc_html_e('Hayır, 18 yaşından küçüğüm', 'hive-ultra-premium'); ?>
            </button>
        </div>
        <p class="hive-age-gate-legal">
            <?php esc_html_e('Devam ederek', 'hive-ultra-premium'); ?>
            <a href="<?php echo esc_url(hive_legal_page_url('kullanim-sartlari')); ?>" target="_blank" rel="noopener noreferrer"><?php esc_html_e('Kullanım Şartları', 'hive-ultra-premium'); ?></a>
            <?php esc_html_e('ve', 'hive-ultra-premium'); ?>
            <a href="<?php echo esc_url(hive_legal_page_url('sorumluluk-reddi')); ?>" target="_blank" rel="noopener noreferrer"><?php esc_html_e('Sorumluluk Reddi', 'hive-ultra-premium'); ?></a>
            <?php esc_html_e('metinlerini kabul etmiş olursunuz.', 'hive-ultra-premium'); ?>
        </p>
    </div>
</div>
