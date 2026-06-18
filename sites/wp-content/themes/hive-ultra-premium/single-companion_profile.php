<?php
/**
 * Single companion profile template
 *
 * @package Hive_Ultra_Premium
 */

get_header();

while (have_posts()) :
    the_post();

    $pid          = get_the_ID();
    $yas          = hive_ultra_get_meta($pid, 'yas');
    $telefon      = hive_ultra_get_meta($pid, 'telefon');
    $telegram     = hive_ultra_get_meta($pid, 'telegram');
    $lokasyon     = hive_ultra_get_meta($pid, 'lokasyon');
    $fiyat        = hive_ultra_get_meta($pid, 'fiyat');
    $odeme_sekli  = hive_ultra_get_meta($pid, 'odeme_sekli');
    $ozellikler   = hive_ultra_get_meta($pid, 'ozellikler');
    $terms        = get_the_terms($pid, 'companion_category');
    $odeme        = get_post_meta($pid, 'odeme', true);
    $hizmetler    = get_post_meta($pid, 'hizmetler', true);
    $odeme_labels = array('nakit' => 'Nakit', 'kart' => 'Kredi Kartı', 'kripto' => 'Kripto');
    $hizmet_labels = array(
        'anal' => 'Anal', 'oral' => 'Oral', '24saat' => '24 Saat',
        'otele-gelir' => 'Otele Gelir', 'eve-gelir' => 'Eve Gelir',
        'masaj' => 'Masaj', 'partner' => 'Partner', 'cift' => 'Çift', 'grup' => 'Grup',
    );
    if (!is_array($hizmetler)) {
        $hizmetler = array();
    }
    ?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php if (function_exists('hive_breadcrumb')) {
            hive_breadcrumb();
        } ?>

        <?php get_template_part('template-parts/stories', 'slider', array('profile_id' => $pid)); ?>

        <article <?php post_class('single-profile'); ?>>
            <div class="single-profile-image">
                <?php if (has_post_thumbnail()) : ?>
                    <?php the_post_thumbnail('large', array('loading' => 'eager', 'alt' => esc_attr(get_the_title()))); ?>
                <?php else : ?>
                    <img src="<?php echo esc_url(hive_ultra_placeholder_url()); ?>" alt="<?php the_title_attribute(); ?>" width="800" height="600">
                <?php endif; ?>
                <button class="fav-btn" data-id="<?php echo esc_attr($pid); ?>" aria-label="<?php esc_attr_e('Favorilere ekle', 'hive-ultra-premium'); ?>">♡</button>
            </div>

            <div class="single-profile-content">
                <h1><?php the_title(); ?></h1>

                <div class="profile-details">
                    <table class="profile-details-table">
                        <?php if ($yas) : ?>
                        <tr>
                            <th><?php esc_html_e('Yaş', 'hive-ultra-premium'); ?></th>
                            <td><?php echo esc_html($yas); ?></td>
                        </tr>
                        <?php endif; ?>
                        <?php if ($lokasyon) : ?>
                        <tr>
                            <th><?php esc_html_e('Lokasyon', 'hive-ultra-premium'); ?></th>
                            <td><?php echo esc_html($lokasyon); ?></td>
                        </tr>
                        <?php endif; ?>
                        <?php if ($fiyat) : ?>
                        <tr>
                            <th><?php esc_html_e('Fiyat', 'hive-ultra-premium'); ?></th>
                            <td class="price-cell"><?php echo esc_html($fiyat); ?> ₺</td>
                        </tr>
                        <?php endif; ?>
                        <?php if ($odeme_sekli) : ?>
                        <tr>
                            <th><?php esc_html_e('Ödeme', 'hive-ultra-premium'); ?></th>
                            <td><?php echo esc_html($odeme_sekli); ?></td>
                        </tr>
                        <?php endif; ?>
                        <?php if ($ozellikler) : ?>
                        <tr>
                            <th><?php esc_html_e('Özellikler', 'hive-ultra-premium'); ?></th>
                            <td><?php echo esc_html($ozellikler); ?></td>
                        </tr>
                        <?php endif; ?>
                        <?php if ($telefon) : ?>
                        <tr>
                            <th><?php esc_html_e('Telefon', 'hive-ultra-premium'); ?></th>
                            <td><span id="profile-phone" class="phone-hidden"><?php echo esc_html($telefon); ?></span></td>
                        </tr>
                        <?php endif; ?>
                    </table>

                    <?php if (!empty($hizmetler)) : ?>
                    <div class="profile-services">
                        <?php foreach ($hizmetler as $h) : ?>
                            <span class="service-badge"><?php echo esc_html($hizmet_labels[$h] ?? $h); ?></span>
                        <?php endforeach; ?>
                    </div>
                    <?php endif; ?>

                    <div class="profile-actions">
                        <?php if ($telefon) : ?>
                            <button type="button" id="reveal-phone" class="btn btn-primary"><?php esc_html_e('İletişim Bilgilerini Göster', 'hive-ultra-premium'); ?></button>
                        <?php endif; ?>
                        <?php if ($telegram && ($tg_url = hive_ultra_telegram_url($telegram))) : ?>
                            <a href="<?php echo esc_url($tg_url); ?>" target="_blank" rel="noopener" class="btn btn-telegram">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="white" style="vertical-align:middle;margin-right:6px"><path d="M11.944 0A12 12 0 000 12a12 12 0 0012 12 12 12 0 0012-12A12 12 0 0012 0a12 12 0 00-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 01.171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                                <?php esc_html_e("Telegram'dan Yaz", 'hive-ultra-premium'); ?>
                            </a>
                        <?php endif; ?>
                    </div>
                </div>

                <div class="profile-description"><?php the_content(); ?></div>

                <?php hive_render_profile_video($pid); ?>

                <?php comments_template(); ?>
            </div>
        </article>

        <?php hive_render_profile_map($pid); ?>

        <?php
        $term_ids = $terms && !is_wp_error($terms) ? wp_list_pluck($terms, 'term_id') : array();
        $similar_args = array(
            'post_type'      => 'companion_profile',
            'posts_per_page' => 6,
            'post__not_in'   => array($pid),
            'orderby'        => 'rand',
        );
        if ($term_ids) {
            $similar_args['tax_query'] = array(
                array(
                    'taxonomy' => 'companion_category',
                    'field'    => 'term_id',
                    'terms'    => $term_ids,
                ),
            );
        }
        $similar = new WP_Query($similar_args);
        if ($similar->have_posts()) :
            ?>
            <section class="similar-profiles">
                <?php
                get_template_part('template-parts/slide', 'section', array(
                    'title' => '👥 ' . __('Benzer Profiller', 'hive-ultra-premium'),
                    'query' => $similar,
                ));
                ?>
            </section>
            <?php
        endif;
        wp_reset_postdata();
        ?>
    </div>
</main>

    <?php
endwhile;

get_footer();
