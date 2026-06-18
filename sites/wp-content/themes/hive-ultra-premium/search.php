<?php
/**
 * Search results template
 *
 * @package Hive_Ultra_Premium
 */

get_header();
?>

<main id="main-content" class="site-main">
    <div class="container">
        <header class="section-header">
            <h1>
                <?php
                printf(
                    esc_html__('Arama: %s', 'hive-ultra-premium'),
                    '<span style="color: var(--color-accent);">' . esc_html(get_search_query()) . '</span>'
                );
                ?>
            </h1>
        </header>

        <p class="archive-description" style="margin-bottom:1rem;">
            <?php esc_html_e('İlan adı, Telegram kullanıcı adı, kategori, lokasyon, özellik ve hizmetlerde arama yapılır.', 'hive-ultra-premium'); ?>
        </p>

        <div class="search-form-wrap">
            <?php
            if (function_exists('hive_render_unified_search')) {
                hive_render_unified_search(array('id' => 'hive-search-page', 'live' => true));
            } else {
                get_search_form();
            }
            ?>
        </div>

        <?php if (have_posts()) : ?>
            <div class="profiles-list search-results">
                <?php
                while (have_posts()) :
                    the_post();
                    if (get_post_type() === 'companion_profile') {
                        hive_ultra_get_profile_row(get_post());
                    } else {
                        ?>
                        <article class="profile-row">
                            <div class="profile-row-info" style="flex-grow:1;">
                                <h3 class="profile-row-title">
                                    <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
                                </h3>
                                <div class="profile-row-meta"><?php echo esc_html(get_post_type_object(get_post_type())->labels->singular_name); ?></div>
                            </div>
                            <div class="profile-row-button">
                                <a href="<?php the_permalink(); ?>"><?php esc_html_e('Görüntüle', 'hive-ultra-premium'); ?></a>
                            </div>
                        </article>
                        <?php
                    }
                endwhile;
                ?>
            </div>

            <div class="pagination">
                <?php the_posts_pagination(); ?>
            </div>
        <?php else : ?>
            <div class="no-results">
                <p><?php esc_html_e('Aramanızla eşleşen sonuç bulunamadı.', 'hive-ultra-premium'); ?></p>
                <a href="<?php echo esc_url(home_url('/')); ?>" class="btn btn-primary"><?php esc_html_e('Ana Sayfaya Dön', 'hive-ultra-premium'); ?></a>
            </div>
        <?php endif; ?>
    </div>
</main>

<?php get_footer(); ?>
