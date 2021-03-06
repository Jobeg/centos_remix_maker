from package    import extract_package_list, get_existing_package, get_missing_package, extract_repo_list, download_packages
from os         import path, makedirs, geteuid, listdir, remove
from sys        import argv, stderr
from platform   import machine
from shutil     import copytree, copyfile
from utils      import mount_iso, umount, make_iso, find_files, sed
from tree       import Tree
from repo       import init_repodata, find_os_repodata, cleaning_repodata
from remote     import download_iso

def remix_environnement( treeDirs, kickstart ):
    if not path.exists( treeDirs.cache_path ):
        makedirs( treeDirs.cache_path )
    if not path.exists( treeDirs.iso_original_path ):
        makedirs( treeDirs.iso_original_path )


def read_discinfo( treeDirs ):
    discinfo = ""
    with open( path.join( treeDirs.iso_custom_path, ".discinfo"), "r" ) as f:
        discinfo = f.readlines()[0].strip()
    return discinfo


def add_kickstart_to_isolinux( treeDirs, kickstart, name ):
    isolinux_dir    = path.join( treeDirs.iso_custom_path, "isolinux" )
    isolinux_cfg    = path.join( isolinux_dir, "isolinux.cfg")
    sed( isolinux_cfg, "initrd=initrd.img", "initrd=initrd.img linux ks=cdrom:/ks.cfg", 1 )
    sed( isolinux_cfg, "Welcome to CentOS", "Welcome to " + name, 1 )
    new_kickstart = path.join( treeDirs.iso_custom_path, "ks.cfg")
    if path.exists( new_kickstart ):
        remove( new_kickstart )
    copyfile( kickstart, new_kickstart )
        


if __name__ == "__main__":

    if len(argv) != 6:
        stderr.write( argv[0] + " <kickstart> <working directory> <version> <arch> name" )
        stderr.write( "[Error] You need to provides a kickstart file" )
        stderr.write( "[Error] You need to provides a path to working directory" )
    #elif argv[4] != machine():
    #     stderr.write( "[Error] You need to run this program under mock to emulate arch: " + machine() )

    kickstart   = argv[1]
    workDir     = argv[2]
    version     = argv[3]
    arch        = argv[4]
    iso_name    = argv[5]
    releasever  = version.split('.')[0]
    treeDirs    = Tree( workDir )

    euid = geteuid()
    if euid != 0:
        raise EnvironmentError, "need to be root"
        exit()
    
    remix_environnement( treeDirs, kickstart )

    isoFile             = download_iso( version, arch, treeDirs.workDir )

    if listdir( treeDirs.iso_original_path ) == []:
        mount_iso( isoFile, treeDirs.iso_original_path )
    if not path.exists( treeDirs.iso_custom_path ):
        copytree( treeDirs.iso_original_path, treeDirs.iso_custom_path )

    cleaning_repodata( treeDirs )

    discinfo            = read_discinfo( treeDirs )
    repos               = extract_repo_list( kickstart )
    repodata_list       = init_repodata( repos, treeDirs, discinfo )

    packagesNeed        = extract_package_list( kickstart, repodata_list )

    packagesOrigin      = get_existing_package( path.join( treeDirs.iso_custom_path, "Packages") )

    packagesToDownload  = get_missing_package( packagesNeed, packagesOrigin, repodata_list, verbose = True )

    download_packages( treeDirs.iso_custom_path, packagesToDownload, repodata_list )

    add_kickstart_to_isolinux( treeDirs, kickstart, iso_name )

    try:
        make_iso( "{0}_{1}".format(iso_name,version), treeDirs.iso_custom_path )
    except:
        pass

    if len(listdir( treeDirs.iso_original_path )) > 0:
        umount( treeDirs.iso_original_path )
