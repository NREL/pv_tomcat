/**

Compile with something like:

/Applications/COMSOL53a/Multiphysics/bin/comsol compile -jdkroot `/usr/libexec/java_home -v 1.8*` /full/path/to/TOMCAT_TMY.java

Place the .class file in the same location as a TOMCAT_input.csv and a TOMCAT_tilt.txt file.

Run from the COMSOL GUI or from the terminal with something like:

/Applications/COMSOL53a/Multiphysics/bin/comsol batch -inputfile /full/path/to/TOMCAT_TMY.class

**/

import java.io.*;
import com.comsol.model.*;
import com.comsol.model.util.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

public class TOMCAT_TMY {

  public static Model run() {
    Model model = ModelUtil.create("Model");

    // This sets the COMSOL modelPath to wherever the .class file currently sits
    // This means that COMSOL_input.csv and TOMCAT_tilt.txt are always loaded from the same location at the .class file
    ClassLoader loader = TOMCAT_TMY.class.getClassLoader();
    File file = new File( loader.getResource(TOMCAT_TMY.class.getSimpleName() + ".class").getPath() );
    model.modelPath(file.getParent().toString() + "/");

    model.label("TOMCATModel.mph");

    // This loads the first line of TOMCAT_tilt.txt and interprets it as a tilt in degrees
    String tilt = new String( "" );
    Path tilt_file = Paths.get(model.modelPath() + "TOMCAT_tilt.txt");
    try {
        List<String> lines = Files.readAllLines(tilt_file);
        tilt = lines.get(0);
    } catch (IOException e) {
        System.out.println(e);
    }

    // Physical properties and geometry parameters are set here
    model.param().set("thkFrontSheet", "3.2[mm]", "front sheet (usually glass) thickness");
    model.param().set("thkFrontEncapsulant", ".4[mm]", "front encapsulant (usually EVA) thickness");
    model.param().set("thkCell", "150[um]", "cell thickness");
    model.param().set("thkBackEncapsulant", ".4[mm]", "back encapsulant (usually EVA) thickness");
    model.param().set("thkBackSheet", "300[um]", "back sheet (usually multi-layer polymer) thickness");
    model.param().set("thkModule", "thkBackSheet+thkBackEncapsulant+thkCell+thkFrontEncapsulant+thkFrontSheet", "total laminate thickness");
    model.param().set("kFrontSheet", "1[W/m/K]", "front sheet thermal conductivity, from AGC Solite low-iron glass datasheet");
    model.param().set("kFrontEncapsulant", ".26[W/m/K]", "front encapsulant thermal conductivity, measured at NREL for EVA");
    model.param().set("kCell", "148[W/m/K]", "From Lu 2007 for crystalline silicon");
    model.param().set("kBackEncapsulant", "kFrontEncapsulant");
    model.param().set("kBackSheet", ".26[W/m/K]", "back sheet thermal conductivity, measured at NREL for a PVF-PET-EVA backsheet");
    model.param().set("epsFrontSheet", "0.88", "front sheet thermal emissivity, measured at NREL for Solite low-iron glass");
    model.param().set("epsBackSheet", "0.87", "back sheet thermal emissivity, measured at NREL for a PVF-PET-EVA backsheet");
    model.param().set("epsGround", "0.88", "value for concrete from Incropera Dewitt p931");
    model.param().set("tilt", tilt+"[deg]");
    model.param().set("hAboveGround", ".5[m]", "height of bottom edge above ground");
    model.param().set("hModule", "1[m]", "slant height of the module (measured along the tilted surface)");
    model.param().set("convectionLengthFactor", ".56", "fitting parameter to modify flat plate convection for a tilted module");
    model.param().set("rowPitch", "2*hModule/cos(tilt)", "a simple rule of thumb for tilt-dependent row spacing");
    model.param().set("efficiencyElectricalSTC", "0.171", "STC efficiency of the module");
    model.param().set("efficiencyElectricalTempCo", "-0.0039", "temperature coefficient of the module, in K^-1");
    model.param().set("densityFrontSheet", "2500[kg/m^3]", "from AGC Solite low-iron glass datasheet");
    model.param().set("densityFrontEncapsulant", "960[kg/m^3]", "front encapsulant density from Armstrong 2010 for EVA");
    model.param().set("densityBackEncapsulant", "densityFrontEncapsulant");
    model.param().set("densityBackSheet", "1200[kg/m^3]", "back sheet density, from Jones 2001");
    model.param().set("densityCell", "2330[kg/m^3]", "cell density, from Jones 2001");
    model.param().set("specificHeatFrontSheet", "720[J/kg/K]", "front sheet specific heat, from AGC Solite low-iron glass datasheet");
    model.param().set("specificHeatFrontEncapsulant", "2090[J/kg/K]", "front encapsulant specific heat, from Armstrong 2010 for EVA");
    model.param().set("specificHeatBackEncapsulant", "specificHeatFrontEncapsulant");
    model.param().set("specificHeatBackSheet", "1250[J/kg/K]", "back sheet specific heat, from Jones 2001");
    model.param().set("specificHeatCell", "677[J/kg/K]", "cell specific heat, from Jones 2001");
    model.param().set("irradBackFraction", "0.1", "fraction of the front irradiance that falls on the module's back surface, measured at NREL on the POOMA test rack");
    model.param().set("absBackSheet", "0.33", "solar-weighted absorptivity of the backsheet, measured at NREL for a PVF-PET-EVA backsheet");

    model.component().create("comp1", false);

    model.component("comp1").geom().create("geom1", 2);

    model.file().create("res3");

    model.result().table().create("tbl1", "Table");
    model.result().table().create("tbl2", "Table");
    model.result().table().create("tbl3", "Table");
    model.result().table().create("tbl4", "Table");

    model.func().create("an2", "Analytic");
    model.func().create("an3", "Analytic");
    model.func().create("int1", "Interpolation");

    model.func("an2").label("ground temperature");
    model.func("an2").set("funcname", "temp_ground_striped");
    model.func("an2").set("args", "x, t");
    model.func("an2").set("argunit", "m,s");
    model.func("an2").set("fununit", "K");
    model.func("an2").set("expr", "if(shade(x, t) && (temp(t) < temp_ground(t)), temp(t), temp_ground(t))");

    model.func("an3").label("shade function");
    model.func("an3").set("funcname", "shade");
    model.func("an3").set("args", "x, t");
    model.func("an3").set("argunit", "m, s");
    model.func("an3")
         .set("expr", "if(elevation_projected(t)>0, (mod(x+hAboveGround*cot(pi - elevation_projected(t)),rowPitch)>0&&mod(x+hAboveGround*cot(pi - elevation_projected(t)),rowPitch)+hModule*cot(pi - elevation_projected(t))*sin(tilt)<hModule*cos(tilt)), 1)");

    model.func("int1").label("metHistory");
    model.func("int1")
         .set("funcs", new String[][]{{"temp", "1"},
            {"temp_sky", "2"},
            {"temp_ground", "3"},
            {"poai", "4"},
            {"dni", "5"},
            {"wind_speed", "6"},
            {"elevation_projected", "7"},
            {"abs_glass", "8"},
            {"abs_encapsulant", "9"},
            {"abs_cell", "10"},
            {"current_factor", "11"}});
    model.func("int1").set("source", "file");
    model.func("int1").set("filename", model.modelPath() + "TOMCAT_input.csv");
    model.func("int1").set("nargs", 1);

    model.component("comp1").mesh().create("mesh1");

    model.component("comp1").geom("geom1").repairTolType("relative");
    model.component("comp1").geom("geom1").create("r1", "Rectangle");
    model.component("comp1").geom("geom1").feature("r1").label("module laminate");
    model.component("comp1").geom("geom1").feature("r1").set("pos", new String[]{"0", "hAboveGround"});
    model.component("comp1").geom("geom1").feature("r1").set("rot", "tilt");
    model.component("comp1").geom("geom1").feature("r1")
         .set("layername", new String[]{"FrontSheet", "FrontEncapsulant", "Cell", "BackEncapsulant"});
    model.component("comp1").geom("geom1").feature("r1")
         .set("layer", new String[]{"thkFrontSheet", "thkFrontEncapsulant", "thkCell", "thkBackEncapsulant"});
    model.component("comp1").geom("geom1").feature("r1").set("layerbottom", false);
    model.component("comp1").geom("geom1").feature("r1").set("layertop", true);
    model.component("comp1").geom("geom1").feature("r1")
         .set("size", new String[]{"hModule", "thkFrontSheet+thkFrontEncapsulant+thkCell+thkBackEncapsulant+thkBackSheet"});
    model.component("comp1").geom("geom1").create("ls1", "LineSegment");
    model.component("comp1").geom("geom1").feature("ls1").label("ground");
    model.component("comp1").geom("geom1").feature("ls1").set("specify1", "coord");
    model.component("comp1").geom("geom1").feature("ls1").set("coord1", new String[]{"-10[m]", "0"});
    model.component("comp1").geom("geom1").feature("ls1").set("specify2", "coord");
    model.component("comp1").geom("geom1").feature("ls1").set("coord2", new String[]{"10[m]", "0"});
    model.component("comp1").geom("geom1").create("pol2", "Polygon");
    model.component("comp1").geom("geom1").feature("pol2").label("back of previous row");
    model.component("comp1").geom("geom1").feature("pol2").set("x", "-rowPitch,-rowPitch+hModule*cos(tilt)");
    model.component("comp1").geom("geom1").feature("pol2").set("y", "hAboveGround,hAboveGround+hModule*sin(tilt)");
    model.component("comp1").geom("geom1").create("pol4", "Polygon");
    model.component("comp1").geom("geom1").feature("pol4").label("front of previous row");
    model.component("comp1").geom("geom1").feature("pol4")
         .set("x", "-rowPitch-thkModule*sin(tilt),-rowPitch+hModule*cos(tilt)-thkModule*sin(tilt)");
    model.component("comp1").geom("geom1").feature("pol4")
         .set("y", "hAboveGround+thkModule*cos(tilt),hAboveGround+hModule*sin(tilt)+thkModule*cos(tilt)");
    model.component("comp1").geom("geom1").create("pol3", "Polygon");
    model.component("comp1").geom("geom1").feature("pol3").label("back of next row");
    model.component("comp1").geom("geom1").feature("pol3").set("x", "rowPitch,rowPitch+hModule*cos(tilt)");
    model.component("comp1").geom("geom1").feature("pol3").set("y", "hAboveGround,hAboveGround+hModule*sin(tilt)");
    model.component("comp1").geom("geom1").create("pol5", "Polygon");
    model.component("comp1").geom("geom1").feature("pol5").label("front of next row");
    model.component("comp1").geom("geom1").feature("pol5")
         .set("x", "rowPitch-thkModule*sin(tilt),rowPitch+hModule*cos(tilt)-thkModule*sin(tilt)");
    model.component("comp1").geom("geom1").feature("pol5")
         .set("y", "hAboveGround+thkModule*cos(tilt),hAboveGround+hModule*sin(tilt)+thkModule*cos(tilt)");
    model.component("comp1").geom("geom1").feature("fin").set("repairtoltype", "relative");
    model.component("comp1").geom("geom1").run();
    model.component("comp1").geom("geom1").run("r1");

    model.component("comp1").variable().create("var1");
    model.component("comp1").variable("var1")
         .set("power", "poai(t*1[1/s])*current_factor(t*1[1/s])*(efficiencyElectricalSTC*(1+efficiencyElectricalTempCo[1/K]*(aveop1(T)-298.15[K])))");

    model.component("comp1").material().create("mat1", "Common");
    model.component("comp1").material().create("mat2", "Common");
    model.component("comp1").material().create("mat3", "Common");
    model.component("comp1").material().create("mat4", "Common");
    model.component("comp1").material().create("mat5", "Common");
    model.component("comp1").material().create("mat6", "Common");
    model.component("comp1").material().create("mat7", "Common");
    model.component("comp1").material().create("mat8", "Common");
    model.component("comp1").material().create("mat9", "Common");
    model.component("comp1").material("mat1").selection().set(new int[]{1});
    model.component("comp1").material("mat2").selection().set(new int[]{2});
    model.component("comp1").material("mat3").selection().set(new int[]{3});
    model.component("comp1").material("mat4").selection().set(new int[]{4});
    model.component("comp1").material("mat5").selection().set(new int[]{5});
    model.component("comp1").material("mat6").selection().geom("geom1", 1);
    model.component("comp1").material("mat6").selection().set(new int[]{1});
    model.component("comp1").material("mat7").selection().geom("geom1", 1);
    model.component("comp1").material("mat7").selection().set(new int[]{5});
    model.component("comp1").material("mat8").selection().geom("geom1", 1);
    model.component("comp1").material("mat8").selection().set(new int[]{14});

    model.component("comp1").cpl().create("bndsim1", "BoundarySimilarity");
    model.component("comp1").cpl().create("bndsim2", "BoundarySimilarity");
    model.component("comp1").cpl().create("bndsim3", "BoundarySimilarity");
    model.component("comp1").cpl().create("bndsim4", "BoundarySimilarity");
    model.component("comp1").cpl().create("aveop1", "Average");
    model.component("comp1").cpl("bndsim1").selection().set(new int[]{14});
    model.component("comp1").cpl("bndsim2").selection().set(new int[]{5});
    model.component("comp1").cpl("bndsim3").selection().set(new int[]{14});
    model.component("comp1").cpl("bndsim4").selection().set(new int[]{5});
    model.component("comp1").cpl("aveop1").selection().set(new int[]{3});

    model.component("comp1").physics().create("ht", "HeatTransfer", "geom1");
    model.component("comp1").physics("ht").feature("solid1").create("opq1", "Opacity", 2);
    model.component("comp1").physics("ht").create("hf1", "HeatFluxBoundary", 1);
    model.component("comp1").physics("ht").feature("hf1").selection().set(new int[]{5, 14});
    model.component("comp1").physics("ht").create("hf2", "HeatFluxBoundary", 1);
    model.component("comp1").physics("ht").feature("hf2").selection().set(new int[]{5, 14});
    model.component("comp1").physics("ht").create("hs1", "HeatSource", 2);
    model.component("comp1").physics("ht").feature("hs1").selection().set(new int[]{3});
    model.component("comp1").physics("ht").create("hs2", "HeatSource", 2);
    model.component("comp1").physics("ht").feature("hs2").selection().set(new int[]{1});
    model.component("comp1").physics("ht").create("hs3", "HeatSource", 2);
    model.component("comp1").physics("ht").feature("hs3").selection().set(new int[]{2});
    model.component("comp1").physics("ht").create("hs4", "HeatSource", 2);
    model.component("comp1").physics("ht").feature("hs4").selection().set(new int[]{4});
    model.component("comp1").physics("ht").create("hs5", "HeatSource", 2);
    model.component("comp1").physics("ht").feature("hs5").selection().set(new int[]{5});
    model.component("comp1").physics("ht").create("hf5", "HeatFluxBoundary", 1);
    model.component("comp1").physics("ht").feature("hf5").selection().set(new int[]{14});
    model.component("comp1").physics().create("rad", "Radiation", "geom1");
    model.component("comp1").physics("rad").selection().set(new int[]{1, 2, 3, 5, 14, 20, 21});
    model.component("comp1").physics("rad").create("opq1", "Opacity", 2);
    model.component("comp1").physics("rad").feature("opq1").selection().all();
    model.component("comp1").physics("rad").create("ds1", "DiffuseSurface", 1);
    model.component("comp1").physics("rad").feature("ds1").selection().set(new int[]{5, 14});
    model.component("comp1").physics("rad").create("ds2", "DiffuseSurface", 1);
    model.component("comp1").physics("rad").feature("ds2").selection().set(new int[]{1});
    model.component("comp1").physics("rad").create("ds3", "DiffuseSurface", 1);
    model.component("comp1").physics("rad").feature("ds3").selection().set(new int[]{3});
    model.component("comp1").physics("rad").create("ds4", "DiffuseSurface", 1);
    model.component("comp1").physics("rad").feature("ds4").selection().set(new int[]{20});
    model.component("comp1").physics("rad").create("ds5", "DiffuseSurface", 1);
    model.component("comp1").physics("rad").feature("ds5").selection().set(new int[]{21});
    model.component("comp1").physics("rad").create("ds6", "DiffuseSurface", 1);
    model.component("comp1").physics("rad").feature("ds6").selection().set(new int[]{2});

    model.component("comp1").mesh("mesh1").create("edg1", "Edge");
    model.component("comp1").mesh("mesh1").create("map1", "Map");
    model.component("comp1").mesh("mesh1").create("cpe1", "CopyEdge");
    model.component("comp1").mesh("mesh1").create("cpe2", "CopyEdge");
    model.component("comp1").mesh("mesh1").feature("edg1").selection().set(new int[]{1});
    model.component("comp1").mesh("mesh1").feature("edg1").create("size1", "Size");
    model.component("comp1").mesh("mesh1").feature("edg1").create("dis1", "Distribution");
    model.component("comp1").mesh("mesh1").feature("map1").create("dis1", "Distribution");
    model.component("comp1").mesh("mesh1").feature("map1").create("size2", "Size");
    model.component("comp1").mesh("mesh1").feature("map1").create("dis2", "Distribution");
    model.component("comp1").mesh("mesh1").feature("map1").create("dis3", "Distribution");
    model.component("comp1").mesh("mesh1").feature("map1").feature("dis1").selection()
         .set(new int[]{4, 6, 8, 10, 12});
    model.component("comp1").mesh("mesh1").feature("map1").feature("size2").selection().geom("geom1", 2);
    model.component("comp1").mesh("mesh1").feature("map1").feature("size2").selection().set(new int[]{1, 2, 3, 4, 5});

    model.capeopen().label("Thermodynamics Package");

    model.component("comp1").material("mat1").label("FrontSheet");
    model.component("comp1").material("mat1").propertyGroup("def")
         .set("thermalconductivity", new String[]{"kFrontSheet", "0", "0", "0", "kFrontSheet", "0", "0", "0", "kFrontSheet"});
    model.component("comp1").material("mat1").propertyGroup("def").set("density", "densityFrontSheet");
    model.component("comp1").material("mat1").propertyGroup("def").set("heatcapacity", "specificHeatFrontSheet");
    model.component("comp1").material("mat2").label("FrontEncapsulant");
    model.component("comp1").material("mat2").propertyGroup("def")
         .set("thermalconductivity", new String[]{"kFrontEncapsulant", "0", "0", "0", "kFrontEncapsulant", "0", "0", "0", "kFrontEncapsulant"});
    model.component("comp1").material("mat2").propertyGroup("def").set("density", "densityFrontEncapsulant");
    model.component("comp1").material("mat2").propertyGroup("def")
         .set("heatcapacity", "specificHeatFrontEncapsulant");
    model.component("comp1").material("mat3").label("Cell");
    model.component("comp1").material("mat3").propertyGroup("def")
         .set("thermalconductivity", new String[]{"kCell", "0", "0", "0", "kCell", "0", "0", "0", "kCell"});
    model.component("comp1").material("mat3").propertyGroup("def").set("density", "densityCell");
    model.component("comp1").material("mat3").propertyGroup("def").set("heatcapacity", "specificHeatCell");
    model.component("comp1").material("mat4").label("BackEncapsulant");
    model.component("comp1").material("mat4").propertyGroup("def")
         .set("thermalconductivity", new String[]{"kBackEncapsulant", "0", "0", "0", "kBackEncapsulant", "0", "0", "0", "kBackEncapsulant"});
    model.component("comp1").material("mat4").propertyGroup("def").set("density", "densityBackEncapsulant");
    model.component("comp1").material("mat4").propertyGroup("def").set("heatcapacity", "specificHeatBackEncapsulant");
    model.component("comp1").material("mat5").label("BackSheet");
    model.component("comp1").material("mat5").propertyGroup("def")
         .set("thermalconductivity", new String[]{"kBackSheet", "0", "0", "0", "kBackSheet", "0", "0", "0", "kBackSheet"});
    model.component("comp1").material("mat5").propertyGroup("def").set("density", "densityBackSheet");
    model.component("comp1").material("mat5").propertyGroup("def").set("heatcapacity", "specificHeatBackSheet");
    model.component("comp1").material("mat6").label("GroundSurface");
    model.component("comp1").material("mat6").propertyGroup("def").set("emissivity", "epsGround");
    model.component("comp1").material("mat7").label("FrontSurface");
    model.component("comp1").material("mat7").propertyGroup("def").set("emissivity", "epsFrontSheet");
    model.component("comp1").material("mat8").label("BackSurface");
    model.component("comp1").material("mat8").propertyGroup("def").set("emissivity", "epsBackSheet");
    model.component("comp1").material("mat9").label("Ground");
    model.component("comp1").material("mat9").propertyGroup("def")
         .set("thermalconductivity", new String[]{"1.8[W/(m*K)]", "0", "0", "0", "1.8[W/(m*K)]", "0", "0", "0", "1.8[W/(m*K)]"});
    model.component("comp1").material("mat9").propertyGroup("def").set("density", "2300[kg/m^3]");
    model.component("comp1").material("mat9").propertyGroup("def").set("heatcapacity", "880[J/(kg*K)]");

    model.component("comp1").cpl("bndsim1").label("back surface to previous row");
    model.component("comp1").cpl("bndsim1").selection("destination").set(new int[]{3});
    model.component("comp1").cpl("bndsim2").label("front surface to next row");
    model.component("comp1").cpl("bndsim2").selection("destination").set(new int[]{20});
    model.component("comp1").cpl("bndsim3").label("back surface to next row");
    model.component("comp1").cpl("bndsim3").selection("destination").set(new int[]{21});
    model.component("comp1").cpl("bndsim4").label("front surface to previous row");
    model.component("comp1").cpl("bndsim4").selection("destination").set(new int[]{2});

    model.component("comp1").physics("ht").feature("solid1").label("Heat Transfer in Solids 1");
    model.component("comp1").physics("ht").feature("solid1").feature("opq1").label("Opaque 1");
    model.component("comp1").physics("ht").feature("init1").set("Tinit", "temp(t*1[1/s])");
    model.component("comp1").physics("ht").feature("hf1").set("q0", "rad.rflux");
    model.component("comp1").physics("ht").feature("hf1").label("radiation flux");
    model.component("comp1").physics("ht").feature("hf2").set("HeatFluxType", "ConvectiveHeatFlux");
    model.component("comp1").physics("ht").feature("hf2").set("HeatTransferCoefficientType", "ExtForcedConvection");
    model.component("comp1").physics("ht").feature("hf2").set("Lpl", "hModule*convectionLengthFactor");
    model.component("comp1").physics("ht").feature("hf2").set("U", "wind_speed(t*1[1/s])");
    model.component("comp1").physics("ht").feature("hf2").set("Text", "temp(t*1[1/s])");
    model.component("comp1").physics("ht").feature("hf2").label("convection flux");
    model.component("comp1").physics("ht").feature("hs1").set("Q0", "(abs_cell(t*1[1/s]) - power)/thkCell");
    model.component("comp1").physics("ht").feature("hs1").label("absorption in cell");
    model.component("comp1").physics("ht").feature("hs2").set("Q0", "abs_glass(t*1[1/s])/thkFrontSheet");
    model.component("comp1").physics("ht").feature("hs2").label("absorption in front sheet");
    model.component("comp1").physics("ht").feature("hs3").set("Q0", "abs_encapsulant(t*1[1/s])/thkFrontEncapsulant");
    model.component("comp1").physics("ht").feature("hs3").label("absorption in front encapsulant");
    model.component("comp1").physics("ht").feature("hs4").label("absorption in back encapsulant");
    model.component("comp1").physics("ht").feature("hs5").label("absorption in back sheet");
    model.component("comp1").physics("ht").feature("hf5").set("q0", "irradBackFraction*poai(t*1[1/s])*absBackSheet");
    model.component("comp1").physics("ht").feature("hf5").label("incident rear irradiance");
    model.component("comp1").physics("rad").feature("opq1").label("Opaque 1");
    model.component("comp1").physics("rad").feature("ds1").set("RadiationDirectionType", "RadiationDirectionPlus");
    model.component("comp1").physics("rad").feature("ds1").set("defineAmbientTemperatureOnEachSide", false);
    model.component("comp1").physics("rad").feature("ds1").set("Tamb", "temp_sky(t*1[1/s])");
    model.component("comp1").physics("rad").feature("ds1").set("Tambu", "TAmbientRadiation");
    model.component("comp1").physics("rad").feature("ds1").label("module surface");
    model.component("comp1").physics("rad").feature("ds2").set("RadiationDirectionType", "RadiationDirectionPlus");
    model.component("comp1").physics("rad").feature("ds2").set("defineAmbientTemperatureOnEachSide", false);
    model.component("comp1").physics("rad").feature("ds2").set("Tamb", "temp_sky(t*1[1/s])");
    model.component("comp1").physics("rad").feature("ds2").set("minput_temperature", "temp_ground_striped(x, t)");
    model.component("comp1").physics("rad").feature("ds2").label("ground");
    model.component("comp1").physics("rad").feature("ds3").set("RadiationDirectionType", "RadiationDirectionMinus");
    model.component("comp1").physics("rad").feature("ds3").set("defineAmbientTemperatureOnEachSide", false);
    model.component("comp1").physics("rad").feature("ds3").set("Tamb", "temp_sky(t*1[1/s])");
    model.component("comp1").physics("rad").feature("ds3").set("epsilon_rad", "epsBackSheet");
    model.component("comp1").physics("rad").feature("ds3").set("minput_temperature", "bndsim1(T)");
    model.component("comp1").physics("rad").feature("ds3").label("back of previous row");
    model.component("comp1").physics("rad").feature("ds4").set("RadiationDirectionType", "RadiationDirectionPlus");
    model.component("comp1").physics("rad").feature("ds4").set("defineAmbientTemperatureOnEachSide", false);
    model.component("comp1").physics("rad").feature("ds4").set("Tamb", "temp_sky(t*1[1/s])");
    model.component("comp1").physics("rad").feature("ds4").set("epsilon_rad", "epsFrontSheet");
    model.component("comp1").physics("rad").feature("ds4").set("minput_temperature", "bndsim2(T)");
    model.component("comp1").physics("rad").feature("ds4").label("front of next row");
    model.component("comp1").physics("rad").feature("ds5").set("RadiationDirectionType", "RadiationDirectionMinus");
    model.component("comp1").physics("rad").feature("ds5").set("defineAmbientTemperatureOnEachSide", false);
    model.component("comp1").physics("rad").feature("ds5").set("Tamb", "temp_sky(t*1[1/s])");
    model.component("comp1").physics("rad").feature("ds5").set("epsilon_rad", "epsBackSheet");
    model.component("comp1").physics("rad").feature("ds5").set("minput_temperature", "bndsim3(T)");
    model.component("comp1").physics("rad").feature("ds5").label("back of next row");
    model.component("comp1").physics("rad").feature("ds6").set("RadiationDirectionType", "RadiationDirectionPlus");
    model.component("comp1").physics("rad").feature("ds6").set("defineAmbientTemperatureOnEachSide", false);
    model.component("comp1").physics("rad").feature("ds6").set("Tamb", "temp_sky(t*1[1/s])");
    model.component("comp1").physics("rad").feature("ds6").set("epsilon_rad", "epsFrontSheet");
    model.component("comp1").physics("rad").feature("ds6").set("minput_temperature", "bndsim4(T)");
    model.component("comp1").physics("rad").feature("ds6").label("front of previous row");

    model.component("comp1").mesh("mesh1").feature("edg1").feature("size1").set("custom", "on");
    model.component("comp1").mesh("mesh1").feature("edg1").feature("size1").set("hmax", "hModule/6");
    model.component("comp1").mesh("mesh1").feature("edg1").feature("size1").set("hmaxactive", true);
    model.component("comp1").mesh("mesh1").feature("edg1").feature("dis1").active(false);
    model.component("comp1").mesh("mesh1").feature("edg1").feature("dis1").set("numelem", 1);
    model.component("comp1").mesh("mesh1").feature("map1").feature("dis1").set("numelem", 2);
    model.component("comp1").mesh("mesh1").feature("map1").feature("size2").set("custom", "on");
    model.component("comp1").mesh("mesh1").feature("map1").feature("size2").set("hmax", "100[mm]");
    model.component("comp1").mesh("mesh1").feature("map1").feature("size2").set("hmaxactive", true);
    model.component("comp1").mesh("mesh1").feature("map1").feature("dis2").set("numelem", 1);
    model.component("comp1").mesh("mesh1").feature("map1").feature("dis3").set("numelem", 1);
    model.component("comp1").mesh("mesh1").feature("cpe1").selection("source").set(new int[]{14});
    model.component("comp1").mesh("mesh1").feature("cpe1").selection("destination").set(new int[]{3, 21});
    model.component("comp1").mesh("mesh1").feature("cpe2").selection("source").set(new int[]{5});
    model.component("comp1").mesh("mesh1").feature("cpe2").selection("destination").set(new int[]{2, 20});
    model.component("comp1").mesh("mesh1").run();

    model.frame("material1").sorder(1);

    model.component("comp1").physics("rad").feature("ds1").set("minput_temperature_src", "root.comp1.T");
    model.component("comp1").physics("rad").feature("ds3").set("epsilon_rad_mat", "userdef");
    model.component("comp1").physics("rad").feature("ds4").set("epsilon_rad_mat", "userdef");
    model.component("comp1").physics("rad").feature("ds5").set("epsilon_rad_mat", "userdef");
    model.component("comp1").physics("rad").feature("ds6").set("epsilon_rad_mat", "userdef");

    model.study().create("std1");
    model.study("std1").create("time", "Transient");

    model.sol().create("sol1");
    model.sol("sol1").study("std1");
    model.sol("sol1").attach("std1");
    model.sol("sol1").create("st1", "StudyStep");
    model.sol("sol1").create("v1", "Variables");
    model.sol("sol1").create("t1", "Time");
    model.sol("sol1").feature("t1").create("fc1", "FullyCoupled");
    model.sol("sol1").feature("t1").create("d1", "Direct");
    model.sol("sol1").feature("t1").feature().remove("fcDef");

    model.result().dataset().create("cpt1", "CutPoint2D");

    model.result().numerical().create("av1", "AvLine");
    model.result().numerical("av1").selection().set(new int[]{14});
    model.result().numerical("av1").set("probetag", "none");

    model.result().numerical().create("av2", "AvSurface");
    model.result().numerical("av2").selection().set(new int[]{3});
    model.result().numerical("av2").set("probetag", "none");

    model.result().numerical().create("gev1", "EvalGlobal");
    model.result().numerical("gev1").set("probetag", "none");

    model.result().numerical().create("pev1", "EvalPoint");
    model.result().numerical("pev1").set("probetag", "none");

    return model;
  }

  public static Model run2(Model model) {
    model.result().create("pg1", "PlotGroup2D");
    model.result("pg1").create("arwl1", "ArrowLine");
    model.result("pg1").create("arwl2", "ArrowLine");
    model.result("pg1").create("surf1", "Surface");
    model.result("pg1").create("line1", "Line");
    model.result("pg1").feature("line1").create("sel1", "Selection");
    model.result("pg1").feature("line1").feature("sel1").selection().set(new int[]{1});
    model.result().export().create("anim1", "Animation");

    model.study("std1").feature("time").set("tlist", "range(0,3600,365*86400)");

    model.sol("sol1").attach("std1");
    model.sol("sol1").feature("t1").set("atolglobalvaluemethod", "manual");
    model.sol("sol1").feature("t1").set("fieldselection", "comp1_T");
    model.sol("sol1").feature("t1").set("atolmethod", new String[]{"comp1_T", "global", "comp1_rad_J", "global"});
    model.sol("sol1").feature("t1")
         .set("atolvaluemethod", new String[]{"comp1_T", "manual", "comp1_rad_J", "manual"});
    model.sol("sol1").feature("t1").set("atolfactor", new String[]{"comp1_T", "0.1", "comp1_rad_J", "0.1"});
    model.sol("sol1").feature("t1").set("atol", new String[]{"comp1_T", "1e-3", "comp1_rad_J", "1e-3"});
    model.sol("sol1").feature("t1").set("atoludot", new String[]{"comp1_T", "1e-3", "comp1_rad_J", "1e-3"});
    model.sol("sol1").feature("t1").set("tstepsbdf", "strict");
    model.sol("sol1").feature("t1").set("maxorder", 2);
    model.sol("sol1").feature("t1").set("estrat", "exclude");
    model.sol("sol1").feature("t1").feature("dDef").set("ooc", false);
    model.sol("sol1").feature("t1").feature("aDef").set("blocksize", 100);
    model.sol("sol1").feature("t1").feature("aDef").set("blocksizeactive", true);
    model.sol("sol1").feature("t1").feature("fc1").set("maxiter", 5);
    model.sol("sol1").feature("t1").feature("fc1").set("damp", 0.9);
    model.sol("sol1").feature("t1").feature("fc1").set("jtech", "once");
    model.sol("sol1").feature("t1").feature("d1").set("linsolver", "pardiso");
    model.sol("sol1").feature("t1").feature("d1").set("ooc", false);
    model.sol("sol1").runAll();

    model.result().dataset("cpt1").set("pointx", "hModule*cos(tilt)/2");
    model.result().dataset("cpt1").set("pointy", "hModule*sin(tilt)/2+hAboveGround");

    model.result().numerical("av2").label("cell temperature");
    model.result().numerical("av2").set("table", "tbl2");
    model.result().numerical("av2").set("unit", new String[]{"degC"});
    model.result().numerical("av2").setResult();
    model.result().table("tbl2").save(model.modelPath()+"ModelOutput_Temperature.csv");

    model.result().numerical("gev1").label("power");
    model.result().numerical("gev1").set("table", "tbl3");
    model.result().numerical("gev1").set("expr", new String[]{"power"});
    model.result().numerical("gev1").set("unit", new String[]{"1"});
    model.result().numerical("gev1").set("descr", new String[]{"power"});
    model.result().numerical("gev1").setResult();
    model.result().table("tbl3").save(model.modelPath()+"ModelOutput_Power.csv");

    model.result("pg1").set("looplevel", new int[]{1});
    model.result("pg1").set("edges", false);
    model.result("pg1").feature("arwl1")
         .set("expr", new String[]{"-rad.rflux*nx*(rad.rflux>0)", "-rad.rflux*ny*(rad.rflux>0)"});
    model.result("pg1").feature("arwl1").set("descractive", true);
    model.result("pg1").feature("arwl1").set("descr", "radiation heat flux");
    model.result("pg1").feature("arwl1").set("arrowbase", "head");
    model.result("pg1").feature("arwl1").set("scale", 0.001);
    model.result("pg1").feature("arwl1").set("scaleactive", true);
    model.result("pg1").feature("arwl1").set("arrowcount", 500);
    model.result("pg1").feature("arwl1").set("color", "custom");
    model.result("pg1").feature("arwl1")
         .set("customcolor", new double[]{0.8980392217636108, 0.5098039507865906, 0.4000000059604645});
    model.result("pg1").feature("arwl1").set("inheritarrowscale", false);
    model.result("pg1").feature("arwl1").set("inheritcolor", false);
    model.result("pg1").feature("arwl1").set("inheritrange", false);
    model.result("pg1").feature("arwl1").set("inheritdeformscale", false);
    model.result("pg1").feature("arwl2")
         .set("expr", new String[]{"-rad.rflux*nx*(rad.rflux<0)", "-rad.rflux*ny*(rad.rflux<0)"});
    model.result("pg1").feature("arwl2").set("descractive", true);
    model.result("pg1").feature("arwl2").set("descr", "radiation heat flux");
    model.result("pg1").feature("arwl2").set("scale", 0.001);
    model.result("pg1").feature("arwl2").set("scaleactive", true);
    model.result("pg1").feature("arwl2").set("arrowcount", 500);
    model.result("pg1").feature("arwl2").set("color", "custom");
    model.result("pg1").feature("arwl2")
         .set("customcolor", new double[]{0.22745098173618317, 0.5254902243614197, 0.7372549176216125});
    model.result("pg1").feature("arwl2").set("inheritplot", "arwl1");
    model.result("pg1").feature("arwl2").set("inheritarrowscale", false);
    model.result("pg1").feature("arwl2").set("inheritcolor", false);
    model.result("pg1").feature("surf1").set("unit", "degC");
    model.result("pg1").feature("line1").set("colortable", "WaveLight");
    model.result("pg1").feature("surf1").set("resolution", "normal");
    model.result("pg1").feature("line1").set("expr", "temp_ground_striped(x,t)");
    model.result("pg1").feature("line1").set("descr", "temp_ground_striped(x,t)");
    model.result("pg1").feature("line1").set("colortable", "WaveLight");
    model.result("pg1").feature("line1").set("resolution", "normal");
    model.result().export("anim1").set("target", "player");
    model.result().export("anim1").set("framesel", "all");
    model.result().export("anim1").set("synchronize", false);

    return model;
  }

  public static void main(String[] args) {
    Model model = run();
    run2(model);
  }

}