/* First-party, machine-ID-only allowlist extracted from the bundled MAME 0.289
 * driver registration tables (pacman.cpp + galaxian.cpp). No ROM metadata,
 * downloads or game assets. Keep in sync when rebuilding MAME. */
export const ARCADE_MACHINES = Object.freeze([
  'galaxian','galaxiana','galaxianm','galaxianmo','galaxiant','galaxiani','superg','supergs','fntspcian','galturbo','galap1','galap2',
  'galap4','zerotime','galaktron','galaktrons3','galkamika','zerotimed','zerotimemc','zerotimea','zerotimeb','galaxcirsa','starfght','galaxbsf',
  'galaxianbl','galaxbsf2','galaxiamv','galaxianbl2','galaxianbl3','galaxianoly','galaxianem','galaxrf','galaxrfgg','galaxrcgg','galaxianrp','galaxyx',
  'mcwars','galartic','galaxianiii','sgalwars','moonaln','galapx','kamikazp','supergx','swarm','astrians','tst_galx','blkhole',
  'orbitron','luctoday','chewing','catacomb','omegab','highroll','guttangt','guttangts3','bmxstunts','victoryc','victorycb','warofbug',
  'warofbugg','warofbugu','spactrai','rocktcnvy','redufo','redufob','redufob2','redufob3','exodus','tdpgal','tdpgala','kamakazi3',
  'spacian2','azurian','pisces','piscesb','omni','supershp','uniwars','uniwarsa','mltiwars','gteikoku','gteikokub','gteikokub2',
  'gteikokub3','spacbatt','spacbat2','spacempr','skyraidr','galemp','asideral','pajaroes','vueloesp','streakng','streaknga','pacmanbl',
  'pacmanbla','pacmanblb','pacmanblc','pacmanblci','pacmanblco','komemokos','pacmanblv','pacmanblva','crazym','ghostmun','phoenxp2','batman2',
  'ladybugg','ladybugg2','atlantisb','tenspot','devilfshg','devilfshgb','zigzagb','zigzagb2','gmgalax','fourplay','videight','mooncrst',
  'mooncrstuk','mooncrstuku','mooncrstu','mooncrstuu','mooncrsto','mooncrstg','mooncrsts','eagle','eagle2','eagle3','mooncrsb','mooncrs2',
  'mooncrs3','mooncrs4','mooncrs5','fantazia','spctbird','smooncrs','meteora','mooncrstso','mooncptc','mouncrst','sirio2','ataqandr',
  'mutacion','sstarcrs','mooncmw','starfgmc','spcdrag','floritas','floritasm','mooncreg','mooncreg2','mooncrsl','mooncrecm','stera',
  'mooncrgx','moonqsr','moonal2','moonal2b','galactica2','thepitm','bongo','bongog','ckongg','ckongmc','ckongmc2','ckonggx',
  'ckongcv','ckongis','bigkonggx','bagmanmc','bagmanm2','bagmanm3','porter','portera','skybase','kong','fantastc','timefgtr',
  'jumpbug','jumpbugb','jumpbugbrf','jumpbugbc','olibug','levers','checkman','checkmanj','dingo','dingoe','mshuttle','mshuttle2',
  'mshuttlea','mshuttlej','mshuttlej2','kingball','kingballj','frogger','froggers1','froggers2','froggers3','froggermc','froggers','frogf',
  'frogg','froggeg','froggrs','froggervd','froggereb','quaak','froggeram','turtles','turpin','turpins','turpinnv','froggert',
  'amidar','amidar1','amidaru','amidaro','amidarb','amidarb2','amidarc','amigo','amigo2','amidars','mandinga','mandingaeg',
  'mandingag','mandinka','mandingarf','mandingac','olmandingo','olmandingc','theend','theends','theendss','takeoff','scramble','scrambles',
  'scrambles2','strfbomb','explorer','scramblebf','scrambp','spctrek','scramce','scrampt','scramrf','offensiv','ncentury','scrammr',
  'scramblebb','scramblebun','kamikazesp','bomber','spcmission','astroamb','seainv','atlantis','atlantis2','ozon1','ckongs','jungsub',
  'scorpion','scorpiona','scorpionb','scorpionmc','aracnis','aracnisa','skelagon','monsterz','monsterza','scobra','scobrase','scobras',
  'scobrae','scobrae2','scobrab','scobrag','scobraggi','suprheli','moonwar','moonwara','armorcar','armorcar2','tazmania','mimonkey',
  'mimonsco','mimonscr','mimonscra','anteater','anteateruk','anteaterg','anteatergg','calipso','losttomb','losttombh','spdcoin','superbon',
  'superbona','namenayo','sbhoei','sbhoeia','puckman','puckmanb','puckmanf','puckmanh','puckmanb3','pacman','pacmanso','pacmanvg',
  'pacmanf','puckmod','pacmod','pacmanjpm','pacmanmr','pacmanpe','newpuc2','newpuc2b','newpuckx','pacheart','bucaner','bucanera',
  'hangly','hangly2','hangly3','baracuda','popeyeman','pacuman','crockman','crockmnf','puckmana','joyman','ctrpllrp','piranha',
  'piranhao','mspacmab3','mspacmab5','abscam','piranhah','titanpac','pacmanfm','pacmanug','pacplus','mspacman','mspacmnf','mspacmat',
  'msheartb','pacgal2','mspacmancr','mspacmab','mspacmab2','mspacmab4','mspacmab6','mspacmbe','mspacmbmc','mspacmbn','mspacmanlai','mspacmane',
  'mspacmane2','mspacii','mspacii2','pacgal','mspacpls','mschamp','mschamps','mspackpls','mspacmanhnc','mspacmanbg','mspacmanbg2','mspacmanbgd',
  'mspacmanbgf','mspacmanblt','mspacmanblt2','mspacmanblt3','mspacmanblt4','mspacmanbcc','mspacmanbhe','mspacmanbco','mspacmanbi','mspacmanbgc','mspacmanbpl','pacmansp',
  'mspactwin','mspactwina','clubpacm','clubpacma','jumpshot','jumpshotp','shootbul','crush','crush2','crush3','crush4','crush5',
  'maketrax','maketrxb','korosuke','crushrlf','crushbl','crushbl2','crushbl3','crushs','mbrush','paintrlr','painter','eyes',
  'eyes2','eyesb','eyeszac','eyeszacb','mrtnt','gorkans','lizwiz','eggor','birdiy','woodpeck','woodpeca','nmouse',
  'nmouseb','ponpoko','ponpokov','candory','alibaba','alibabab','dremshpr','vanvan','vanvank','vanvanb','bwcasino','acitya',
  'theglobp','theglobpa','theglobme','sprglobp','sprglobp2','sprglbpg','beastfp','beastfpa','eeekkp','drivfrcp','porky','rocktrv2',
  'bigbucks','numcrash','cannonbp','superabc','superabco','pengojpm','pengopac','pengomc1','pengomc2','pinguinos',
]);
const MACHINE_IDS = new Set(ARCADE_MACHINES);
export function arcadeMachine(filename) {
  const match = /^([a-z][a-z0-9_]{1,30})\.zip$/i.exec(String(filename || '').trim());
  const id = match?.[1]?.toLowerCase();
  return id && MACHINE_IDS.has(id) ? id : null;
}
export function isArcadeMachine(id) { return MACHINE_IDS.has(id); }
