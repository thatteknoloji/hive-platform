<?php
/**
 * Tekil gece hayatı mekan rehberi
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <?php
        while (have_posts()) :
            the_post();
            $phone = get_post_meta(get_the_ID(), 'mekan_telefon', true);
            $insta = get_post_meta(get_the_ID(), 'mekan_instagram', true);
            $adres = get_post_meta(get_the_ID(), 'mekan_adres', true);
            ?>
            <article <?php post_class('gece-hayati-single'); ?>>
                <?php if (function_exists('hive_breadcrumb')) {
                    hive_breadcrumb();
                } ?>
                <header class="section-header">
                    <h1><?php the_title(); ?></h1>
                    <div class="gece-hayati-single-tax">
                        <?php the_terms(get_the_ID(), 'gece_mahalle', '<span class="gece-tax">', '</span>'); ?>
                        <?php the_terms(get_the_ID(), 'gece_saat', '<span class="gece-tax">', '</span>'); ?>
                        <?php the_terms(get_the_ID(), 'gece_tur', '<span class="gece-tax">', '</span>'); ?>
                    </div>
                    <?php if ($phone || $insta || $adres) : ?>
                        <div class="gece-hayati-contact">
                            <?php if ($adres) : ?><p>📍 <?php echo esc_html($adres); ?></p><?php endif; ?>
                            <?php if ($phone) : ?><p>📞 <?php echo esc_html($phone); ?></p><?php endif; ?>
                            <?php if ($insta) : ?><p>📸 <?php echo esc_html($insta); ?></p><?php endif; ?>
                        </div>
                    <?php endif; ?>
                </header>
                <div class="gece-hayati-content entry-content">
                    <?php the_content(); ?>
                </div>
                <?php
                $related = function_exists('hive_gece_related_posts') ? hive_gece_related_posts(get_the_ID(), 6) : array();
                if ($related) :
                    ?>
                    <section class="gece-hayati-related">
                        <h2><?php esc_html_e('Bağlantılı Rehberler', 'hive-ultra-premium'); ?></h2>
                        <ul>
                            <?php foreach ($related as $rp) : ?>
                                <li><a href="<?php echo esc_url(get_permalink($rp)); ?>"><?php echo esc_html(get_the_title($rp)); ?></a></li>
                            <?php endforeach; ?>
                        </ul>
                    </section>
                <?php endif; ?>
            </article>
        <?php endwhile; ?>
    </div>
</main>

<?php get_footer(); ?>
