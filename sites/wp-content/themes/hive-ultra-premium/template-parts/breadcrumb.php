<?php
/**
 * Breadcrumb navigation
 *
 * @package Hive_Ultra_Premium
 */
?>
<nav class="hive-breadcrumb" aria-label="<?php esc_attr_e('İçerik haritası', 'hive-ultra-premium'); ?>">
    <ol itemscope itemtype="https://schema.org/BreadcrumbList">
        <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
            <a itemprop="item" href="<?php echo esc_url(home_url('/')); ?>">
                <span itemprop="name"><?php esc_html_e('Ana Sayfa', 'hive-ultra-premium'); ?></span>
            </a>
            <meta itemprop="position" content="1" />
        </li>
        <?php if (is_singular('companion_profile') || is_post_type_archive('companion_profile') || is_tax('companion_category')) : ?>
            <li aria-hidden="true">›</li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <a itemprop="item" href="<?php echo esc_url(get_post_type_archive_link('companion_profile')); ?>">
                    <span itemprop="name"><?php esc_html_e('Profiller', 'hive-ultra-premium'); ?></span>
                </a>
                <meta itemprop="position" content="2" />
            </li>
        <?php endif; ?>
        <?php if (is_singular('companion_profile')) : ?>
            <li aria-hidden="true">›</li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <span itemprop="name"><?php the_title(); ?></span>
                <meta itemprop="position" content="3" />
            </li>
        <?php elseif (is_tax('companion_category')) : ?>
            <li aria-hidden="true">›</li>
            <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                <span itemprop="name"><?php single_term_title(); ?></span>
                <meta itemprop="position" content="3" />
            </li>
        <?php endif; ?>
    </ol>
</nav>
