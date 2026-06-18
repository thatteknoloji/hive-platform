<?php
/**
 * AJAX profile filter bar
 *
 * @package Hive_Ultra_Premium
 */
$locations = hive_ultra_locations();
$target_id = isset($args['target']) ? esc_attr($args['target']) : 'hive-filter-results';
$layout    = isset($args['layout']) ? esc_attr($args['layout']) : 'row';
?>
<div class="hive-filter-bar" data-target="<?php echo $target_id; ?>" data-layout="<?php echo $layout; ?>">
    <div class="hive-filter-grid">
        <div class="hive-filter-field">
            <label><?php esc_html_e('Yaş', 'hive-ultra-premium'); ?></label>
            <div class="hive-range-row">
                <input type="range" class="hive-range" id="hive-yas-min" min="18" max="50" value="20" data-pair="hive-yas-max" />
                <input type="range" class="hive-range" id="hive-yas-max" min="18" max="50" value="38" data-pair="hive-yas-min" />
            </div>
            <span class="hive-range-label"><span id="hive-yas-min-val">20</span> - <span id="hive-yas-max-val">38</span></span>
        </div>
        <div class="hive-filter-field">
            <label><?php esc_html_e('Fiyat (₺)', 'hive-ultra-premium'); ?></label>
            <div class="hive-range-row">
                <input type="range" class="hive-range" id="hive-fiyat-min" min="500" max="8000" step="100" value="1000" />
                <input type="range" class="hive-range" id="hive-fiyat-max" min="500" max="8000" step="100" value="6000" />
            </div>
            <span class="hive-range-label"><span id="hive-fiyat-min-val">1000</span> - <span id="hive-fiyat-max-val">6000</span> ₺</span>
        </div>
        <div class="hive-filter-field">
            <label for="hive-lokasyon"><?php esc_html_e('Lokasyon', 'hive-ultra-premium'); ?></label>
            <select id="hive-lokasyon" class="hive-select">
                <option value=""><?php esc_html_e('Tümü', 'hive-ultra-premium'); ?></option>
                <?php foreach ($locations as $loc) : ?>
                    <option value="<?php echo esc_attr($loc); ?>"><?php echo esc_html($loc); ?></option>
                <?php endforeach; ?>
            </select>
        </div>
        <div class="hive-filter-field">
            <label for="hive-sort"><?php esc_html_e('Sıralama', 'hive-ultra-premium'); ?></label>
            <select id="hive-sort" class="hive-select">
                <option value="newest"><?php esc_html_e('En Yeni', 'hive-ultra-premium'); ?></option>
                <option value="popular"><?php esc_html_e('En Popüler', 'hive-ultra-premium'); ?></option>
                <option value="cheapest"><?php esc_html_e('En Ucuz', 'hive-ultra-premium'); ?></option>
                <option value="expensive"><?php esc_html_e('En Pahalı', 'hive-ultra-premium'); ?></option>
            </select>
        </div>
        <div class="hive-filter-field hive-filter-actions">
            <button type="button" class="btn btn-primary" id="hive-filter-apply"><?php esc_html_e('Uygula', 'hive-ultra-premium'); ?></button>
        </div>
    </div>
</div>
<div id="<?php echo $target_id; ?>" class="hive-filter-results">
    <div class="hive-skeleton-grid" id="hive-skeleton" hidden>
        <?php for ($i = 0; $i < 4; $i++) : ?>
            <div class="hive-skeleton-card"></div>
        <?php endfor; ?>
    </div>
</div>
